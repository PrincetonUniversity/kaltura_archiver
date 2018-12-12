# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
fi


source .git_prompt.sh
myh="$(cat ~/.hostname)"

PS1='[\h] \W$(__git_ps1 " (%s)")]\$ '
export PS1='$myh \[\e[0;31m\]\w\e[0m\] \[\e[0;34m\]$(__git_ps1)\e[0m\] '

