# Google Sign-In Setup Instructions

## 1. Install Dependencies
```bash
pip install -r requirements.txt
```

## 2. Set up Google OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (or Google Identity API)
4. Go to "Credentials" in the left sidebar
5. Click "Create Credentials" > "OAuth 2.0 Client IDs"
6. Configure the OAuth consent screen if prompted
7. Choose "Web application" as the application type
8. Add authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback` (for development)
   - `https://yourdomain.com/auth/google/callback` (for production)

## 3. Configure Environment Variables

1. Copy `.env.example` to `.env`
2. Fill in your Google OAuth credentials:
   ```
   GOOGLE_CLIENT_ID=your_actual_client_id
   GOOGLE_CLIENT_SECRET=your_actual_client_secret
   ```

## 4. Set Environment Variables (Windows)
```cmd
set GOOGLE_CLIENT_ID=your_actual_client_id
set GOOGLE_CLIENT_SECRET=your_actual_client_secret
```

## 5. Update Database Schema
Run the migration script to add Google authentication support:
```bash
python add_google_auth.py
```

## 6. Run the Application
```bash
python main.py
```

## How it Works

- Users can now click "Sign in with Google" on the login page
- If it's their first time, a new account is created automatically
- If they already have an account with the same email, their Google account gets linked
- Users can still use traditional username/password login

## Security Notes

- Keep your Google Client Secret secure and never commit it to version control
- Use HTTPS in production
- The redirect URI must exactly match what you configured in Google Cloud Console