package com.code.armor.service;

import com.code.armor.entity.User;
import com.code.armor.exception.ClientErrorException;
import com.code.armor.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository repo;

    public User getByEmail(String email) {
        return repo.findByEmail(email)
                .orElseThrow(() -> new ClientErrorException("USER_404", "User not found"));
    }
}

