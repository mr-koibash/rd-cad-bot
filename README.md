# rd-cad-bot
A bot for exploring AI capabilities in CAD


## 1. Installation
Install packages from *requirements.txt*
```commandline
pip install -r requirements.txt
```

Install <u>**one**</u> of these libraries versions:
### GPU version (CUDA)
*llama_cpp*: 
```commandline
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir
```
*torch*:
```commandline
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
*sentence-transformers*:
```commandline
pip install sentence-transformers
```

*chromadb*:
```commandline
pip install chromadb[gpu]
```

### CPU version
*llama_cpp*: 
```commandline
pip install llama-cpp-python
```
*torch*:
```commandline
pip install torch torchvision torchaudio
```
*sentence-transformers*:
```commandline
pip install sentence-transformers
```

*chromadb*:
```commandline
pip install chromadb
```

## 2. Usage