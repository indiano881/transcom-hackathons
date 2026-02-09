package com.code.armor.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@AllArgsConstructor
public class FileEntityDto {

    private Long id;
    private String fileName;
    private Long size;
    private LocalDateTime uploadedAt;
}
