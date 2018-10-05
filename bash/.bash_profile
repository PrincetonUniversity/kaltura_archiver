# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
fi

export PYENV_ROOT=$HOME/.pyenv
PATH=$PYENV_ROOT/bin:$PATH

export PATH

source .git_prompt.sh
PS1='[\h] \W$(__git_ps1 " (%s)")]\$ '
