package com.code.armor.exception;

import lombok.Getter;

@Getter
public class InternalServerErrorException extends ServerErrorException {

    private static final String ERROR_CODE = "InternalServerError";

    public InternalServerErrorException(String message) {
        super(ERROR_CODE, message);
    }
}
