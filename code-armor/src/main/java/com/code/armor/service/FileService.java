package com.code.armor.service;

import com.code.armor.dto.FileEntityDto;
import com.code.armor.dto.PagedResponse;
import com.code.armor.entity.FileEntity;
import com.code.armor.entity.User;
import com.code.armor.exception.ClientIllegalArgumentException;
import com.code.armor.exception.InternalServerErrorException;
import com.code.armor.mapper.FileEntityMapper;
import com.code.armor.repository.FileRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class FileService {

    @Value("${app.upload.dir}")
    private String uploadDir;

    private final FileRepository fileRepository;
    private final FileEntityMapper fileEntityMapper;

    public void uploadFile(User user, MultipartFile multipartFile) {
        String uuidFileName = UUID.randomUUID() + "-" +
                multipartFile.getOriginalFilename();
        Path target = Path.of(uploadDir, uuidFileName);
        try {
            Files.copy(multipartFile.getInputStream(), target);
        } catch (IOException e) {
            throw new InternalServerErrorException("Failed to store file. Please try again later.");
        }
        FileEntity entity = new FileEntity();
        entity.setUser(user);
        entity.setFileName(multipartFile.getOriginalFilename());
        entity.setStorageName(uuidFileName);
        entity.setSize(multipartFile.getSize());
        fileRepository.save(entity);
    }

    public void deleteFile(User user, long id) {
        FileEntity file = fileRepository.findById(id)
                .orElseThrow(() -> new ClientIllegalArgumentException("File not found"));
        if(!file.getUser().getId().equals(user.getId())){
            throw new ClientIllegalArgumentException("File not found");
        }
        try {
            Files.deleteIfExists(Path.of(uploadDir, file.getStorageName()));
        } catch (IOException e) {
            throw new InternalServerErrorException("Failed to delete file. Please try again later.");
        }
        fileRepository.delete(file);
    }

    public PagedResponse<FileEntityDto> listFiles(User user, int page, int pageSize) {
        Pageable pageable = PageRequest.of(page - 1, pageSize,
                Sort.by(Sort.Direction.DESC, "uploadedAt"));
        Page<FileEntity> fileEntityPage = fileRepository.findByUserId(user.getId(), pageable);
        List<FileEntityDto> fileEntityDtoList = fileEntityPage.stream()
                .map(fileEntityMapper::toDto)
                .toList();
        return new PagedResponse<>(fileEntityDtoList, fileEntityPage.getTotalElements());
    }
}

