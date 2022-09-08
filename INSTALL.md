## Installing BARAM

### Supported Platforms
- Ubuntu 20.04 or newer
- CentOS 8.2 or newer
- Windows 10 or newer
- macOS 10.14 or newer

### BARAM requires following installed software:

- Python 3.9.x or newer
- [MS-MPI](https://docs.microsoft.com/en-us/message-passing-interface/microsoft-mpi) 10.0 or newer ( Windows Only )
- OpenMPI 4.0 or newer ( Linux, macOS )

### Clone the source code
```commandline
git clone http://210.16.192.68/nextfoam/baram.git
```

### Setup Python virtual environment

Run following command in the top directory of downloaded source code

```commandline
python3 -m venv venv
```

### Enter into virtual environment
Run following command in the top directory of downloaded source code

#### On Windows
```commandline
.\venv\Scripts\activate.bat
```

#### On Linux or macOS
```commandline
source ./venv/bin/activate
```

### Install Python packages
Run following command in the top directory of downloaded source code
```commandline
pip install -r requirements.txt
```

### Copy Solver Executables
Download and extract solver executables into the top directory of downloaded source code
#### Windows

#### Linux

#### macOS

### Compile Resource Files
```commandline
python convertUI.py
```

### Run BARAM
```commandline
python main.py
```



Note