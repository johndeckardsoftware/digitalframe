import os, subprocess
import ffmpeg

def check_ffmpeg():
    try:
        # Runs 'ffmpeg -version' and captures the output
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
        return True, "FFmpeg is installed and accessible!"
    except subprocess.CalledProcessError:
        return False, "FFmpeg found, but it returned an error."
    except FileNotFoundError:
        return False, "FFmpeg is NOT installed or not in your system PATH."

def extract_mp3_from_video(file):
    try:
        filemp3 = file + ".mp3"
        input_file = ffmpeg.input(file)
        audio = input_file.audio
        output = ffmpeg.output(audio, filemp3)
        _, err = ffmpeg.run(output, quiet=True, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        return True, None, filemp3
    except ffmpeg.Error as e:
        err = e.stderr.decode('utf8')
        if "Failed to set value '0:a' for option 'map'" in err: # no audio
            return False, None, None
        else:
            return False, err, None
    except Exception as e:
        return False, str(e), None

def extract_sound(file):
    ret, err = check_ffmpeg()
    if ret: ret, err, filemp3 = extract_mp3_from_video(file)
    else: filemp3 = None
    return ret, err, filemp3
