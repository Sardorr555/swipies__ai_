"""Trusted bounded openat collector. Runs after the user main has exited."""
import base64,json,os,signal,stat

try:
    os.kill(-1,signal.SIGSTOP)
except ProcessLookupError:
    pass  # No remaining user process besides this collector and PID 1.
files=[]; total=0; entries=0
flags=os.O_RDONLY|os.O_NOFOLLOW
def collect(directory,prefix=''):
    global total,entries
    for name in sorted(os.listdir(directory)):
        entries+=1
        if entries>100: raise ValueError('Too many artifact entries')
        st=os.stat(name,dir_fd=directory,follow_symlinks=False)
        if stat.S_ISDIR(st.st_mode):
            fd=os.open(name,flags|os.O_DIRECTORY,dir_fd=directory)
            try: collect(fd,prefix+name+'/')
            finally: os.close(fd)
        else:
            if not stat.S_ISREG(st.st_mode): raise ValueError('Artifact must be a regular file')
            total+=st.st_size
            if total>10*1024*1024 or len(files)>=20: raise ValueError('Artifact size/count limit exceeded')
            fd=os.open(name,flags|os.O_NONBLOCK,dir_fd=directory)
            with os.fdopen(fd,'rb') as f: raw=f.read(10*1024*1024+1)
            if len(raw)!=st.st_size: raise ValueError('Artifact changed during collection')
            files.append({'name':prefix+name,'size':len(raw),'content_b64':base64.b64encode(raw).decode()})
fd=os.open('/workspace/artifacts',flags|os.O_DIRECTORY)
try: collect(fd)
finally: os.close(fd)
print(json.dumps(files))
