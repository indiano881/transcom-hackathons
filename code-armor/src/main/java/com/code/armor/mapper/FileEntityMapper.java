package com.code.armor.mapper;

import com.code.armor.dto.FileEntityDto;
import com.code.armor.entity.FileEntity;
import org.mapstruct.Mapper;

@Mapper(componentModel = "spring")
public interface FileEntityMapper {
    FileEntityDto toDto(FileEntity fileEntity);
}
