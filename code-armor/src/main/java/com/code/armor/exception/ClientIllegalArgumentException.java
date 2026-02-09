package com.code.armor.exception;

import lombok.Getter;

@Getter
public class ClientIllegalArgumentException extends ClientErrorException{

    private static final String ERROR_CODE = "IllegalArgument";

    public ClientIllegalArgumentException(String message) {
        super(ERROR_CODE, message);
    }
}
