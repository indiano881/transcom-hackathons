package com.code.armor.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

@AllArgsConstructor
@Getter
public class ApiErrorResponse {

    private final String code;
    private final String message;
}
