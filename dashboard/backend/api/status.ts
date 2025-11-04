import { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  res.status(200).json({
    success: true,
    data: {
      message: "Trade Analysis Dashboard API is running",
      timestamp: new Date().toISOString(),
      environment: "production"
    }
  });
}