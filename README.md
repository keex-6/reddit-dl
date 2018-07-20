# reddit-dl

## WhatsApp conversion

```python
import subprocess

# convert to h264 (supported by WhatsApp)
try:
    print('converting to h264 encoding...')
    cmd = ('ffmpeg -i {0} -c:v libx264'
            ' -profile:v baseline -y -level 3.0 -strict -2'
            ' -crf 27 -preset ultrafast -pix_fmt yuv420p'
            ' {1}'.format(tmp_f, f))
    subprocess.run(cmd, check=True, shell=True, timeout=22,
        stdout=subprocess.DEVNULL)
    print('conversion complete')
except subprocess.CalledProcessError as exc:
    print('conversion failed', exc.returncode, exc.output)
    return lambda_response(500, {})
except subprocess.TimeoutExpired:
    print('conversion timed out')
    f = tmp_f
```