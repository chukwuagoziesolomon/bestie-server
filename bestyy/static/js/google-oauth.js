// Google OAuth configuration
export const GOOGLE_OAUTH_CONFIG = {
    clientId: 'YOUR_GOOGLE_CLIENT_ID', // Replace with your Google OAuth client ID
    scope: 'profile email',
    redirectUri: 'http://localhost:8000/auth/google/callback',
    authorizationUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    tokenUrl: 'http://localhost:8000/api/auth/google/',
    userInfoUrl: 'https://www.googleapis.com/oauth2/v3/userinfo',
    // Add any additional OAuth parameters as needed
    params: {
        response_type: 'code',
        access_type: 'offline',
        prompt: 'consent',
    }
};

// Function to initiate Google login
export function initiateGoogleLogin() {
    const { clientId, scope, redirectUri, authorizationUrl, params } = GOOGLE_OAUTH_CONFIG;
    
    const queryParams = new URLSearchParams({
        client_id: clientId,
        redirect_uri: redirectUri,
        response_type: params.response_type,
        scope: scope,
        access_type: params.access_type,
        prompt: params.prompt,
    });
    
    window.location.href = `${authorizationUrl}?${queryParams.toString()}`;
}

// Function to handle the OAuth callback
export async function handleGoogleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (code) {
        try {
            const response = await fetch('http://localhost:8000/api/auth/social/google/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code,
                    redirect_uri: GOOGLE_OAUTH_CONFIG.redirectUri,
                }),
            });
            
            if (response.ok) {
                const data = await response.json();
                // Store the tokens
                localStorage.setItem('access_token', data.access);
                localStorage.setItem('refresh_token', data.refresh);
                
                // Redirect to dashboard or home
                window.location.href = '/dashboard/';
            } else {
                console.error('Authentication failed');
                // Handle error
            }
        } catch (error) {
            console.error('Error during authentication:', error);
            // Handle error
        }
    }
}

// Call this function when the callback page loads
if (window.location.pathname === '/auth/google/callback/') {
    handleGoogleCallback();
}
