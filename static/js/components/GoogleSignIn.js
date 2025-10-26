import React, { useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const GoogleSignIn = ({ buttonText = 'Sign in with Google' }) => {
  const navigate = useNavigate();

  useEffect(() => {
    // Load Google API script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const handleCredentialResponse = async (response) => {
    try {
      // Send the credential to your backend
      const API_URL = process.env.REACT_APP_API_URL || 'https://bestie-server.onrender.com';
      const result = await axios.post(`${API_URL}/api/auth/social/google/`, {
        credential: response.credential,
      });

      // Save tokens and user data
      if (result.data.access && result.data.refresh) {
        localStorage.setItem('access_token', result.data.access);
        localStorage.setItem('refresh_token', result.data.refresh);
        
        // Redirect to dashboard or home
        navigate('/dashboard');
      }
    } catch (error) {
      console.error('Error during Google Sign-In:', error);
      // Handle error (show error message to user)
    }
  };

  useEffect(() => {
    // Initialize Google Sign-In button
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: 'YOUR_GOOGLE_CLIENT_ID', // Replace with your actual client ID
        callback: handleCredentialResponse,
      });

      window.google.accounts.id.renderButton(
        document.getElementById('googleSignInButton'),
        { 
          type: 'standard',
          theme: 'outline',
          size: 'large',
          width: 300,
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'left',
        }
      );
    }
  }, []);

  return (
    <div className="google-signin-container">
      <div id="googleSignInButton"></div>
    </div>
  );
};

export default GoogleSignIn;
