package com.code.armor.exception;

import lombok.Getter;

@Getter
public class ServerErrorException extends RuntimeException {

    private final String code;

    public ServerErrorException(String code, String message) {
        super(message);
        this.code = code;
    }
}
