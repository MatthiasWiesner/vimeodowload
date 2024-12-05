import os
import click
import requests
import vimeo
import logging
import json

from concurrent.futures import ThreadPoolExecutor, wait


logger = logging.getLogger('vimeo')


def debug_json(data):
    logger.debug(">>> start debug")
    logger.debug(json.dumps(data, indent=2))
    logger.debug("<<< end debug")


class VimeoDownloader(object):
    def __init__(self, token, verbosity=logging.INFO):
        logger.setLevel(verbosity)
        console_handler = logging.StreamHandler()
        logger.addHandler(console_handler)

        self.client = vimeo.VimeoClient(token=token)

    def iterate_pages(self, file_process_handler, per_page=25, query=None):
        self.file_process_handler = file_process_handler

        next_page = f'/me/videos?per_page={per_page}&page=1&fields=name,files,uri,metadata.connections.texttracks.uri'
        if query:
            next_page = f'{next_page}&query={query}'

        next_page = self._download_page(next_page, per_page)
        while next_page:
            next_page = self._download_page(next_page, per_page)

    def _request_textracks(self, url):
        texttracks = []

        def _texttrack_link(url):
            r = self.client.get(url, timeout=(30,120)).json()
            if not r['data'] or not r['data'][0]['active']:
                return
            texttracks.append({'name': r['data'][0]['name'], 'link': r['data'][0]['link']})
            return r['paging']['next']

        next = url
        while next:
            next = _texttrack_link(next)

        return texttracks

    def _download_page(self, page, per_page):
        executor = ThreadPoolExecutor(max_workers=per_page)
        tasks = []

        try:
            current_result = self.client.get(page, timeout=(30,120)).json()
            if 'error' in current_result:
                logger.error(current_result['error'])
                logger.error(current_result['developer_message'])
                return False

            logger.info(f"Fetch video data from {((current_result['page'] - 1) * per_page) + 1}"
                        + f" to {(current_result['page'] - 1) * per_page + per_page}"
                        + f" of {current_result['total']}")

            # only in debug mode
            debug_json(current_result)

            for vimeo_info in current_result['data']:
                if not 'files' in vimeo_info or not len(vimeo_info['files']):
                    continue

                vimeo_info['texttracks'] = self._request_textracks(vimeo_info['metadata']['connections']['texttracks']['uri'])

                task = executor.submit(self.file_process_handler, vimeo_info)
                tasks.append(task)
            wait(tasks)

        except KeyboardInterrupt:
            executor.shutdown(wait=False, cancel_futures=True)
            logger.error("")
            logger.error("You have to wait until the current page is processed.")
            logger.error("Or you hit CTRL+C multiple times, until it is killed")
            exit()

        return current_result['paging']['next']


@click.group()
@click.option('-t', '--token', help='Vimeo client-token', required=True)
@click.option('-v', '--verbosity', type=click.Choice(['debug', 'info', 'warning', 'error', 'critical']), default='info', help='Logging verbosity')
@click.pass_context
def cli(ctx, token, verbosity):
    verbosity_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    ctx.obj = VimeoDownloader(token, verbosity_map[verbosity])


@cli.command()
@click.option('-p', '--per-page', default=25, help="Determine how many files per page should be listed")
@click.option('-q', '--query', default=None, help="Filter query")
@click.pass_context
def list_videos(ctx, per_page, query):
    """List all your videos at vimeo

    it will printed the vimeo-id, video name and 
    the link to the biggest file in size
    """
    def _list_file(vimeo_info):
        vimeo_id = str(vimeo_info['uri'].split('/')[-1])
        max_size_file_info = max(vimeo_info['files'], key=lambda x: x['size'])
        logger.info(f'{"Vimeo-ID:":>10} {vimeo_id} - {vimeo_info["name"]} - {max_size_file_info["link"]}')

        for texttrack in vimeo_info['texttracks']:
            logger.info(f'{"texttrack:":>14} {texttrack["link"]}')

        return f"Finished {vimeo_id} {vimeo_info['name']}"

    ctx.obj.iterate_pages(_list_file, per_page, query)


@cli.command()
@click.option('-b', '--backuppath', required=True, help="Local path for downloading")
@click.option('-p', '--per-page', default=25, help="Determine how many files per page should be downloaded")
@click.option('-c', '--chunk-size', default=52428800, help="Downloading chunk size, default 50MB")
@click.option('-q', '--query', default=None, help="Filter query")
@click.pass_context
def download_videos(ctx, backuppath, per_page, chunk_size, query):
    """Download all your videos from vimeo

    downloads the link to the biggest file in size
    """
    def _download_file(vimeo_info):
        vimeo_id = str(vimeo_info['uri'].split('/')[-1])
        max_size_file_info = max(vimeo_info['files'], key=lambda x: x['size'])
        ftype = max_size_file_info['type'].split('/')[-1]

        basepath = os.path.join(backuppath, vimeo_info['name'])
        os.path.exists(basepath) or os.mkdir(basepath)

        videofile = os.path.join(basepath, f"{vimeo_info['name']}.{ftype}")
        with open(videofile, 'wb') as bf:
            logger.info(f"Downloaded {vimeo_id}: {videofile}")
            response = requests.get(max_size_file_info['link'], stream=True)
            for chunk in response.iter_content(chunk_size=chunk_size):
                bf.write(chunk)

        if 'texttracks' in vimeo_info:
            texttracks_dir = os.path.join(basepath, 'texttracks')
            os.path.exists(texttracks_dir) or os.mkdir(texttracks_dir)
            for texttrack in vimeo_info['texttracks']:
                logger.info(f"Downloading {texttrack['name']}")
                texttrackfile = os.path.join(texttracks_dir, texttrack['name'])
                with open(texttrackfile, 'wb') as vtt:
                    response = requests.get(texttrack['link'], stream=True)
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        vtt.write(chunk)

    ctx.obj.iterate_pages(_download_file, per_page, query)


if __name__ == '__main__':
    cli()
