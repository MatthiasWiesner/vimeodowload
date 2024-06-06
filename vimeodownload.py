import os
import click
import requests
import vimeo
import logging
import json

logger = logging.getLogger('vimeo')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)


class VimeoDownloader(object):
    def __init__(self, token):
        self.client = vimeo.VimeoClient(token=token)

    def iterate_pages(self, file_process_handler, per_page=25):
        self.file_process_handler = file_process_handler

        next_page = '/me/videos?per_page={0}&page=1&fields=name,files,uri'.format(
            per_page)

        next_page = self._download_page(next_page)

        while next_page:
            next_page = self._download_page(next_page)

    def _download_page(self, page):
        current_result = self.client.get(page).json()
        if 'error' in current_result:
            logger.error(current_result['error'])
            logger.error(current_result['developer_message'])
            return False

        for files_info in current_result['data']:
            if not len(files_info['files']):
                continue
            self.file_process_handler(files_info)
        return current_result['paging']['next']


@click.group()
@click.option('-t', '--token', help='Vimeo client-token', required=True)
@click.pass_context
def cli(ctx, token):
    ctx.obj = VimeoDownloader(token)


@cli.command()
@click.option('-p', '--per-page', default=25, help="Determine how many files per page should be listed")
@click.pass_context
def list_videos(ctx, per_page):
    """List all your videos at vimeo

    it will printed the vimeo-id, video name and 
    the link to the biggest file in size
    """
    def _list_file(files_info):
        vimeo_id = str(files_info['uri'].split('/')[-1])
        max_size_file_info = max(files_info['files'], key=lambda x: x['size'])
        logger.info(f'Vimeo-ID:{vimeo_id} - {files_info["name"]} - {max_size_file_info["link"]}')

    ctx.obj.iterate_pages(_list_file, per_page)


@cli.command()
@click.option('-b', '--backuppath', required=True, help="Local path for downloading")
@click.option('-p', '--per-page', default=25, help="Determine how many files per page should be downloaded")
@click.option('-c', '--chunk-size', default=52428800, help="Downloading chunk size, default 50MB")
@click.pass_context
def download_videos(ctx, backuppath, per_page, chunk_size):
    """Download all your videos from vimeo

    it will printed the vimeo-id, video name and 
    the link to the biggest file in size
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
        logger.info("Done")

    ctx.obj.iterate_pages(_download_file, per_page)
        

if __name__ == '__main__':
    cli()