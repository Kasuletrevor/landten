"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import api, { Landlord, TenantPortalResponse, LoginResponse } from "@/lib/api";

type UserType = "landlord" | "tenant" | null;

interface AuthContextType {
  user: Landlord | TenantPortalResponse | null;
  userType: UserType;
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
  const [user, setUser] = useState<Landlord | TenantPortalResponse | null>(null);
  const [userType, setUserType] = useState<UserType>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const token = api.getToken();
    if (token) {
      // First try as landlord
      api.getMe()
        .then((landlord) => {
          setUser(landlord);
          setUserType("landlord");
          setIsLoading(false);
        })
        .catch(() => {
          // If that fails, try as tenant
          api.getTenantMe()
            .then((tenant) => {
              setUser(tenant);
              setUserType("tenant");
            })
            .catch(() => {
              // Both failed, clear token
              api.setToken(null);
            })
            .finally(() => {
              setIsLoading(false);
            });
        });
    } else {
        // We defer this slightly to avoid the "setState synchronously within an effect" warning
        // if this effect runs immediately on mount
        Promise.resolve().then(() => setIsLoading(false));
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // This login is specifically for landlords as per the original design
    // Tenant login is handled separately in the tenant login page, 
    // but updating the context state is handled by the effect on redirect/reload usually.
    // However, for immediate state update without reload:
    const response: LoginResponse = await api.login(email, password);
    api.setToken(response.access_token);
    setUser(response.landlord);
    setUserType("landlord");
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
      setUserType("landlord");
    },
    []
  );

  const logout = useCallback(() => {
    api.setToken(null);
    setUser(null);
    setUserType(null);
  }, []);

  const updateUser = useCallback(
    async (data: { name?: string; phone?: string }) => {
      if (userType === "landlord") {
        const updated = await api.updateMe(data);
        setUser(updated);
      }
      // Tenant update profile not implemented yet
    },
    [userType]
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        userType,
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
