# rd-cad-bot
A bot for exploring AI capabilities in CAD


### Installation
Install packages from *requirements.txt*
```commandline
pip install -r requirements.txt
```

Install <u>**one**</u> of these *llama_cpp* versions:
1. GPU version (CUDA)
```commandline
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir
```

2. CPU version
```commandline
pip install llama-cpp-python
```