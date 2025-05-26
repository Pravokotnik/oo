@echo off

call npx vite build

if not exist dist\src (
    mkdir dist\src
)

copy src\painter.png dist\src\
copy src\theater.png dist\src\

echo Files copied successfully.
