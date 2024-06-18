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

        next_page = f'/me/videos?per_page={per_page}&page=1&fields=name,files,uri'
        if query:
            next_page = f'/me/videos?per_page={per_page}&page=1&fields=name,files,uri&query={query}'

        next_page = self._download_page(next_page, per_page)
        while next_page:
            next_page = self._download_page(next_page, per_page)

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

            for files_info in current_result['data']:
                if not len(files_info['files']):
                    continue
                task = executor.submit(self.file_process_handler, files_info)
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
    def _list_file(files_info):
        vimeo_id = str(files_info['uri'].split('/')[-1])
        max_size_file_info = max(files_info['files'], key=lambda x: x['size'])
        logger.info(f'{"Vimeo-ID:":>12} {vimeo_id} - {files_info["name"]} - {max_size_file_info["link"]}')
        return f"Finished {vimeo_id} {files_info['name']}"

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
    def _download_file(files_info):
        vimeo_id = str(files_info['uri'].split('/')[-1])
        max_size_file_info = max(files_info['files'], key=lambda x: x['size'])
        ftype = max_size_file_info['type'].split('/')[-1]
        backupfile = os.path.join(backuppath, f"{files_info['name']}.{ftype}")

        with open(backupfile, 'wb') as bf:
            logger.info(f"Downloading {vimeo_id}: {backupfile}")
            response = requests.get(max_size_file_info['link'], stream=True)
            for chunk in response.iter_content(chunk_size=chunk_size):
                bf.write(chunk)

    ctx.obj.iterate_pages(_download_file, per_page, query)


if __name__ == '__main__':
    cli()
