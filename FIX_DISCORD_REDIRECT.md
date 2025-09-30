# Fix Discord OAuth Redirect URI Error

## 🚨 The Problem
You're getting "invalid OAuth2 redirect_URL" because the redirect URI your app is sending doesn't match what's configured in your Discord application.

## 🔧 The Solution

### Step 1: Add ALL These Redirect URIs to Discord

Go to your Discord Developer Portal:
**https://discord.com/developers/applications/1421837492524683374/oauth2/general**

In the "Redirects" section, add **ALL** of these URIs:

```
http://localhost:10000/auth/discord/callback
https://localhost:10000/auth/discord/callback
http://127.0.0.1:10000/auth/discord/callback
https://127.0.0.1:10000/auth/discord/callback
https://recenttablist.onrender.com/auth/discord/callback
http://recenttablist.onrender.com/auth/discord/callback
```

### Step 2: Save the Changes

Click "Save Changes" in the Discord Developer Portal.

### Step 3: Test Again

Try connecting your Discord account again. It should work now!

## 🔍 Debug Information

If it still doesn't work, you can check what redirect URI your app is generating by:

1. Log in as admin
2. Go to: `http://localhost:10000/debug/discord-redirect` (or your domain)
3. This will show you the exact redirect URI being generated
4. Make sure that exact URI is added to your Discord application

## 📋 Common Issues

- **Local vs Production**: Make sure you have redirect URIs for both
- **HTTP vs HTTPS**: Add both versions to be safe
- **Port Numbers**: Include the port number (10000) for local development
- **Trailing Slashes**: Discord is picky about exact matches

## ✅ Expected Result

After adding all the redirect URIs, when you click "Connect" under Discord Account:
1. You'll be redirected to Discord
2. Discord will ask for permission to identify you
3. You'll be redirected back to your profile
4. Your Discord account will be linked!

## 🎯 Why This Happens

Your app generates different redirect URIs depending on:
- Whether you're running locally or on Render
- Whether you're using HTTP or HTTPS
- What domain/port you're accessing from

By adding all possible variations, we ensure it works in all scenarios.