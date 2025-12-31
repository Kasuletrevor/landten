"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import api, { Landlord, LoginResponse } from "@/lib/api";

interface AuthContextType {
  user: Landlord | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    name: string;
    phone?: string;
  }) => Promise<void>;
  logout: () => void;
  updateUser: (data: { name?: string; phone?: string }) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Landlord | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const token = api.getToken();
    if (token) {
      api
        .getMe()
        .then((landlord) => {
          setUser(landlord);
        })
        .catch(() => {
          api.setToken(null);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response: LoginResponse = await api.login(email, password);
    api.setToken(response.access_token);
    setUser(response.landlord);
  }, []);

  const register = useCallback(
    async (data: {
      email: string;
      password: string;
      name: string;
      phone?: string;
    }) => {
      const response: LoginResponse = await api.register(data);
      api.setToken(response.access_token);
      setUser(response.landlord);
    },
    []
  );

  const logout = useCallback(() => {
    api.setToken(null);
    setUser(null);
  }, []);

  const updateUser = useCallback(
    async (data: { name?: string; phone?: string }) => {
      const updated = await api.updateMe(data);
      setUser(updated);
    },
    []
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
