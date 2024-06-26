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
  -t, --token TEXT                Vimeo client-token  [required]
  -v, --verbosity [debug|info|warning|error|critical]
                                  Logging verbosity
  --help                          Show this message and exit.

Commands:
  download-videos  Download all your videos from vimeo
  list-videos      List all your videos at vimeo
```

The script connects to vimeo and fetches all video metadata. Vimeo returns the
metadata in pages. You can adjust how many video files per page are returned.
(`--per-page`, default 25).

Downloading and listing are processed in a thread pool. The thread pool
max-worker size is the per-page size. The download happens in chunks (read and
written). You can adjust the chunk size (`--chunk-size` in Bytes, default 50MB)

The results can be filtered by adding a query parameter. E.g:
`python vimeodownload.py -t {xxxxxxx} list-videos --query teachonline` will only list videos with "teachonline" in the videos name.
(same for downloading)