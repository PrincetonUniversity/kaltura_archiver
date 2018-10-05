# .bashrc
# Source global definitions
if [ -f /etc/bashrc ]; then
	. /etc/bashrc
fi

# User specific aliases and functions

#colorize ls 
alias ls='ls --color=auto' ## Use a long listing format ##
alias ll='ls -la' ## Show hidden files ##
alias l.='ls -d .* --color=auto'

# confirmation #
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
alias ln='ln -i'

#misc
alias vi=vim
alias h='history 25'

