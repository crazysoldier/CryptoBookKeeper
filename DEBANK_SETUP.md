# DeBank API Setup

## Quick Setup Guide

### 1. Sign Up
- Go to: https://cloud.debank.com/
- Register with your email

### 2. Purchase Units
- Click "Purchase units" button
- Pay with USDC
- Units are used for API calls

### 3. Get Your API Key
- Copy your "Access key" from the dashboard
- It looks like: `2c58187bbc44751cac5a2373811ac84206e44347`

### 4. Configure
Add to your `.env` file:
```bash
DEBANK_API_KEY=your_access_key_here
DEBANK_CHAINS=eth,polygon,arbitrum,optimism
```

### 5. Run Export
```bash
make export-debank
```

## Important Notes

✅ **Correct endpoint**: `https://pro-openapi.debank.com/v1` (not api.connect.debank.com)  
✅ **Authentication**: Use `AccessKey` header (not `Bearer`)  
✅ **Rate limit**: 100 requests per second  

That's it! Your on-chain data will be exported to `data/raw/onchain/ethereum/`

