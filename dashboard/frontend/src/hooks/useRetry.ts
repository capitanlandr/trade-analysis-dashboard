import { useState, useCallback } from 'react';

interface UseRetryOptions {
  maxRetries?: number;
  retryDelay?: number;
  backoffMultiplier?: number;
}

interface UseRetryReturn<T> {
  execute: (fn: () => Promise<T>) => Promise<T>;
  isRetrying: boolean;
  retryCount: number;
  reset: () => void;
}

export function useRetry<T = any>(options: UseRetryOptions = {}): UseRetryReturn<T> {
  const {
    maxRetries = 3,
    retryDelay = 1000,
    backoffMultiplier = 2
  } = options;

  const [isRetrying, setIsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const execute = useCallback(async (fn: () => Promise<T>): Promise<T> => {
    let currentRetry = 0;
    setIsRetrying(false);
    setRetryCount(0);

    while (currentRetry <= maxRetries) {
      try {
        const result = await fn();
        setIsRetrying(false);
        setRetryCount(currentRetry);
        return result;
      } catch (error) {
        currentRetry++;
        setRetryCount(currentRetry);

        if (currentRetry > maxRetries) {
          setIsRetrying(false);
          throw error;
        }

        setIsRetrying(true);
        const delay = retryDelay * Math.pow(backoffMultiplier, currentRetry - 1);
        
        console.log(`Retry attempt ${currentRetry}/${maxRetries} in ${delay}ms...`);
        await sleep(delay);
      }
    }

    throw new Error('Max retries exceeded');
  }, [maxRetries, retryDelay, backoffMultiplier]);

  const reset = useCallback(() => {
    setIsRetrying(false);
    setRetryCount(0);
  }, []);

  return {
    execute,
    isRetrying,
    retryCount,
    reset
  };
}