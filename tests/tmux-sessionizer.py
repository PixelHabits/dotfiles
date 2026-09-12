#!/usr/bin/env python3
"""Test session routing with a fake tmux, without contacting an existing server."""
import json, os, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='tmux-projects-') as directory:
    home=Path(directory); tools=home/'bin'; tools.mkdir(); state=home/'sessions.json'; calls=home/'calls'
    stub=tools/'tmux'
    stub.write_text(r"""#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
state=Path(os.environ['STATE']); sessions=json.loads(state.read_text()) if state.exists() else {}
a=sys.argv[1:]
with open(os.environ['CALLS'],'a') as log: log.write(json.dumps(a)+'\n')
if a[0]=='has-session': sys.exit(0 if a[-1].lstrip('=') in sessions else 1)
if a[0]=='new-session': sessions[a[2]]=None
if a[0]=='set-option': sessions[a[2].lstrip('=')]=a[-1]
if a[0]=='show-options': print(sessions.get(a[3].lstrip('='),''))
state.write_text(json.dumps(sessions))
""")
    stub.chmod(0o755)
    env=dict(os.environ,HOME=str(home),PATH=str(tools)+os.pathsep+os.environ['PATH'],STATE=str(state),CALLS=str(calls),TMUX='')
    projects=[home/'a/main',home/'b/main',home/'spaces and quotes' / "a'b"]
    for p in projects: p.mkdir(parents=True)
    def run(*args, extra=None):
        return subprocess.run(['bash',str(ROOT/'dot_local/bin/executable_tmux-sessionizer'),*map(str,args)],env=env | (extra or {}),text=True,capture_output=True)
    for p in projects:
        result=run(p); assert result.returncode==0,result.stderr
    assert len(json.loads(state.read_text()))==3
    before=len([line for line in calls.read_text().splitlines() if 'new-session' in line])
    assert run(projects[0],extra={'TMUX':'fake'}).returncode==0
    after=len([line for line in calls.read_text().splitlines() if 'new-session' in line])
    assert before==after
    assert 'switch-client' in calls.read_text().splitlines()[-1]
    before=calls.read_text()
    assert run(home/'missing').returncode!=0
    assert calls.read_text()==before
    data=json.loads(state.read_text()); name=next(k for k,v in data.items() if v==str(projects[0])); data[name]='other'
    state.write_text(json.dumps(data)); result=run(projects[0]); assert result.returncode!=0 and 'collision' in result.stderr
    # Exercise actual fd discovery of an ignored nested Git worktree.
    import shutil
    finder=shutil.which('fd') or shutil.which('fdfind')
    assert finder, 'fd or fdfind required for discovery test'
    repo=home/'Developer/team/repo';repo.mkdir(parents=True)
    subprocess.run(['git','init','-q',str(repo)],check=True)
    (repo/'.gitignore').write_text('.worktrees/\n')
    nested=repo/'.worktrees/feature';nested.mkdir(parents=True);(nested/'.git').write_text('gitdir: test\n')
    picker=tools/'fzf';picker.write_text('#!/bin/sh\ncat > "$PICKS"\nexit "${PICK_EXIT:-130}"\n');picker.chmod(0o755)
    (tools/'fd').symlink_to(finder)
    env['PICKS']=str(home/'picks')
    assert run().returncode==0
    assert str(nested)+'/' in (home/'picks').read_text()
    assert run(extra={'PICK_EXIT':'2'}).returncode==2
    (tools/'fd').unlink();(tools/'fd').write_text('#!/bin/sh\nexit 42\n');(tools/'fd').chmod(0o755)
    assert run().returncode==42
print('PASS: session routing, path collisions, ignored worktree discovery, finder errors and picker cancellation/errors')
