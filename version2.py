import glob
import os
import re
import subprocess

import time

from pytube import YouTube
from tqdm import tqdm

in_file = 'in.mp4'
PADDING = 0.0  # if it's hard to understand the parts near the cuts, add padding
ONLY_SILENCE = False  # Just for fun


def download_file(url):
    print('Downloading youtube video...')
    name = YouTube(url).streams.first().download()
    os.rename(name, in_file)


def extract_silence_times(text):
    """
    Extracts the silence parts, it's not usable but it's funny
    """
    text_regex = re.compile(r'silence_start: (-?\d+\.?\d*)|silence_end: (\d+\.?\d*)')
    splits = []
    for start, end in text_regex.findall(text):
        if start:
            if float(start) < 0:
                start = 0
            splits.append(float(start) - PADDING)
        if end:
            splits.append(float(end) + PADDING)

    slit_i = iter(splits)

    return list(zip(slit_i, slit_i))


def extract_noise_times(text):
    """
    Extracts the noisy parts by parsing the output of silencedetect
    """
    text_regex = re.compile(r'silence_start: (-?\d+\.?\d*)|silence_end: (\d+\.?\d*)')
    splits = [0]
    for start, end in text_regex.findall(text):
        if start:
            if float(start) < 0:
                start = 0
            splits.append(float(start) - PADDING)
        if end:
            splits.append(float(end) + PADDING)

    # Meaning, keep going until the end of the video
    splits.append(None)

    slit_i = iter(splits)

    times = list(zip(slit_i, slit_i))

    # Remove the first elm if it just (0,0)
    if sum(times[0]) == 0:
        times = times[1:]
    return times


def find_silences(db=-40, duration=0.3):
    """
    Using ffmpeg's silencedetect - finds the parts that we define as silence
    """
    print('Find silence parts...')
    command = (
        f'ffmpeg -i "{in_file}" -af silencedetect=noise={db}dB:duration={duration} -f null - 2> process/vol.txt'
    )
    subprocess.call(command, shell=True)


def process_split(start, end, i):
    to = ''
    if end is not None:
        to = f'-to {end}'

    command = f'ffmpeg -i {in_file} -ss {start} {to} -strict -2 -v warning process/{i}.mp4'
    subprocess.call(command, shell=True)


def concat_parts():
    """
    Merges all the cutted videos inti output file
    """
    command = 'ls -v process/*.mp4 | perl -ne \'print "file $_"\' | ffmpeg -f concat -protocol_whitelist "file,pipe" -i - -c copy -v warning process/out.mp4'
    subprocess.call(command, shell=True)


def clean_old_files():
    files = glob.glob('process/*')
    for f in files:
        os.remove(f)


def get_slices():
    with open('process/vol.txt') as f:
        silence_data = f.read()

    if ONLY_SILENCE:
        return extract_silence_times(silence_data)

    return extract_noise_times(silence_data)


if __name__ == '__main__':
    t0 = time.time()

    download_file(input('Enter youtube url'))

    find_silences()

    clean_old_files()

    slices = get_slices()

    i = 0
    for start, end in tqdm(slices):
        i += 1
        process_split(start, end, i)

    concat_parts()

    print(f'Finished in {time.time() - t0}')

