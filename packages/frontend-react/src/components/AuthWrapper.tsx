import React, { useEffect, useState } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { getCurrentUser, type AuthUser } from 'aws-amplify/auth';
import { configureAmplify } from '../amplify-config';

interface AuthWrapperProps {
  children: React.ReactNode;
}

interface AuthState {
  isLoading: boolean;
  user: AuthUser | null;
  error: string | null;
}

const AuthWrapper: React.FC<AuthWrapperProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isLoading: true,
    user: null,
    error: null,
  });

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Configure Amplify
        configureAmplify();
        
        // Check if user is already signed in
        const user = await getCurrentUser();
        setAuthState({
          isLoading: false,
          user,
          error: null,
        });
      } catch (error) {
        // User is not signed in
        setAuthState({
          isLoading: false,
          user: null,
          error: null,
        });
      }
    };

    initializeAuth();
  }, []);

  // Show loading spinner while checking auth state
  if (authState.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading PulseShrine...</p>
        </div>
      </div>
    );
  }

  // Show error if configuration failed
  if (authState.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Configuration Error</h1>
          <p className="text-gray-600 mb-4">{authState.error}</p>
          <p className="text-sm text-gray-500">
            Please check your environment variables and try again.
          </p>
        </div>
      </div>
    );
  }

  // Custom styling for the Authenticator
  const authComponents = {
    Header() {
      return (
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome to PulseShrine
          </h1>
          <p className="text-gray-600">
            Track your productivity with intelligent AI insights
          </p>
        </div>
      );
    },
  };

  const authFormFields = {
    signUp: {
      email: {
        order: 1,
        placeholder: 'Enter your email address',
      },
      password: {
        order: 2,
        placeholder: 'Create a strong password',
      },
      confirm_password: {
        order: 3,
        placeholder: 'Confirm your password',
      },
    },
    signIn: {
      email: {
        placeholder: 'Enter your email address',
      },
      password: {
        placeholder: 'Enter your password',
      },
    },
  };

  return (
    <Authenticator
      components={authComponents}
      formFields={authFormFields}
      hideSignUp={false}
      loginMechanisms={['email']}
      signUpAttributes={['email']}
    >
      {({ signOut, user }) => (
        <div className="min-h-screen bg-gray-50">
          {/* Navigation Bar */}
          <nav className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="flex items-center">
                  <h1 className="text-xl font-semibold text-gray-900">
                    PulseShrine
                  </h1>
                </div>
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-600">
                    Welcome, {user?.signInDetails?.loginId || user?.username}
                  </span>
                  <button
                    onClick={signOut}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Sign Out
                  </button>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main>
            {children}
          </main>
        </div>
      )}
    </Authenticator>
  );
};

export default AuthWrapper;