class ClientErrorException(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

class ClientIllegalArgumentException(ClientErrorException):
    def __init__(self, message: str):
        super().__init__('IllegalArgument', message)

class ServerErrorException(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

class InternalServerErrorException(ServerErrorException):
    def __init__(self, message: str):
        super().__init__('InternalServerError', message)