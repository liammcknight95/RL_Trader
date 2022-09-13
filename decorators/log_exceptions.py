import traceback, sys, os
import logging
from functools import wraps

log = logging.getLogger('exception_logger')                                  
log.setLevel(logging.WARNING)    
log_format = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')

# writing to file                                                     

try:
    file_handler = logging.FileHandler("./logs/exceptions.log")                             
except FileNotFoundError:
    os.mkdir("./logs")
    logging.basicConfig(filename="./logs/exceptions.log",level=logging.WARNING)
    file_handler = logging.FileHandler("./logs/exceptions.log")
file_handler.setLevel(logging.WARNING)                                        
file_handler.setFormatter(log_format)                          
log.addHandler(file_handler)  

# writing to stdout                                                     
console_handler = logging.StreamHandler(sys.stdout)                             
console_handler.setLevel(logging.WARNING)                                        
console_handler.setFormatter(log_format)                                        
log.addHandler(console_handler)  

def exception_handler(message):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                print(f'running: {func.__name__}')
                return func(*args, **kwargs)
            except:
                print('in error')
                log.error(f'{message.format(func=func)} \n### {traceback.format_exc()}')

        return wrapper
    return decorate