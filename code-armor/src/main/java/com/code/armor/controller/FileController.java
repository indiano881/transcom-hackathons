package com.code.armor.controller;

import com.code.armor.dto.FileEntityDto;
import com.code.armor.dto.PagedResponse;
import com.code.armor.entity.User;
import com.code.armor.security.CustomUserDetails;
import com.code.armor.service.FileService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/file")
@RequiredArgsConstructor
public class FileController {

    private final FileService fileService;

    @PostMapping
    public void uploadFile(@RequestParam("file") MultipartFile multipartFile,
                           @AuthenticationPrincipal CustomUserDetails userDetails){
        fileService.uploadFile(userDetails.getUser(), multipartFile);
    }

    @GetMapping
    public PagedResponse<FileEntityDto> listFiles(
            @AuthenticationPrincipal CustomUserDetails userDetails,
            @RequestParam int pageNo,
            @RequestParam int pageSize
    ){
        User user = userDetails.getUser();
        return fileService.listFiles(user, pageNo, pageSize);
    }

    @DeleteMapping("/{id}")
    public void deleteFile(@PathVariable long id,
                           @AuthenticationPrincipal CustomUserDetails userDetails) {
        fileService.deleteFile(userDetails.getUser(), id);
    }
}
