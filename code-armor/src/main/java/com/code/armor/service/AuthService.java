package com.code.armor.service;

import com.code.armor.dto.AuthResponse;
import com.code.armor.dto.LoginRequest;
import com.code.armor.dto.RegisterRequest;
import com.code.armor.entity.User;
import com.code.armor.exception.ClientErrorException;
import com.code.armor.exception.ClientIllegalArgumentException;
import com.code.armor.repository.UserRepository;
import com.code.armor.security.JwtService;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public void register(RegisterRequest req) {
        if (userRepository.findByEmail(req.getEmail()).isPresent()) {
            throw new ClientIllegalArgumentException("Email already exists");
        }

        User user = new User();
        user.setUsername(req.getUsername());
        user.setEmail(req.getEmail());
        user.setPassword(passwordEncoder.encode(req.getPassword()));
        try {
            userRepository.save(user);
        } catch (DuplicateKeyException e) {
            throw new ClientIllegalArgumentException("Email already exists");
        }
    }

    public AuthResponse login(LoginRequest req) {
        User user = userRepository
                .findByEmail(req.getEmail())
                .orElseThrow(() ->
                        new ClientIllegalArgumentException("Invalid email or password"));

        if (!passwordEncoder.matches(req.getPassword(), user.getPassword())) {
            throw new ClientErrorException("IllegalArgument",
                    "Invalid email or password");
        }
        return new AuthResponse(jwtService.generateToken(user.getEmail()));
    }
}

