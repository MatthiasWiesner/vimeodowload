# Vimeo Video Downloader

Is a helper script to download your videos from Vimeo

Every uploaded video is transformed by Vimeo to multiple videos which differ in size and resolution.
This script downloads the biggest version in size.

## Install
Install requirements with [pipenv](https://pipenv.pypa.io/en/latest/installation.html).

If youre not familiar with pipenv, than you need at least to install `pip`
`apt install python3-pip`
...and install with `pip` the necessary packages:
`pip3 install click requests pyvimeo`

## Run
Currenly two methods are possible
```
> python vimeodownload.py --help
Usage: vimeodownload.py [OPTIONS] COMMAND [ARGS]...

Options:
  -k, --key TEXT     Vimeo client-id  [required]
  -s, --secret TEXT  Vimeo client-secret  [required]
  -t, --token TEXT   Vimeo client-token  [required]
  --help             Show this message and exit.

Commands:
  download-videos  Download all your videos from vimeo
  list-videos      List all your videos at vimeo
```
