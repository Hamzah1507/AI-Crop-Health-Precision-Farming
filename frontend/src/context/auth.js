import { createContext, useContext } from 'react';

// Kept in its own module so AuthContext.jsx exports only a component (required for React Fast Refresh).
export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);
