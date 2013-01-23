colorscheme desert
syntax on
set smartindent
set tabstop=4
set shiftwidth=4
set expandtab
set number
colorscheme koehler
autocmd InsertEnter * syn clear EOLWS | syn match EOLWS excludenl /\s\+\%#\@!$/
autocmd InsertLeave * syn clear EOLWS | syn match EOLWS excludenl /\s\+$/
highlight EOLWS ctermbg=red guibg=red
