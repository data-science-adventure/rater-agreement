# Setup and Installation

## Pre-requisities
- [Python](https://www.python.org/downloads/) is installed
- [Virtual enviroment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) for python is installed

## 1. Create virtual environment

```shell
python3 -m venv .venv
```

## 2. Activate virtual environment:

**For linux and Mac:**

```shell
source .venv/bin/activate
```

**For Windows:**
The correct command to activate a virtual environment on Windows depends on the terminal you're using.

For Command Prompt (CMD): Use the .bat file.

```shell
.venv\Scripts\activate.bat
```
For PowerShell: Use the .ps1 file.

```shell
.venv\Scripts\Activate.ps1
```

### 2.1 Create requirements.txt file (optional)

If you are the maintainer of the project and you have to add new libraries, then you must follow the next steps in order to create the `requirements.txt` file

1. Install pip-tools with the command `pip install pip-tools`
2. Add, update or delete a dependency in the file `requirements.in`
3. Create the file requirements.txt with the command `pip-compile requirements.in`

## 3. Install the project dependencies

```shell
pip install -r requirements.txt
```

## 4. Install the library locally

```shell
pip install -e . 
```
after this, we can execute commands like `info` and `extract` in the next way:

```shell
nlp info
nlp extract
```

## Common tasks

### Cleanning the cache files

In order to delete all the `__python__` cache files, we can execute the next command line in the root folder:

```shell
pyclean .
```
### Update libraries

```shell
python3 update-libs.sh
```

## Commands

### For extract from text
nlp extract text
nlp extract features
nlp extract uml

### For dataset management
nlp dataset split
nlp dataset transform
nlp dataset info

### For inference
nlp inference sentiment
nlp inference image-to-text

### For model operations
nlp model train
