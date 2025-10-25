"""
Evaluation submission utility with retry logic
"""
import asyncio
import httpx
from typing import Dict, Any

from src.core.logger import logger


async def send_evaluation(
    evaluation_url: str, 
    payload: Dict[str, Any], 
    max_retries: int = 5,
    timeout: float = 30.0
) -> bool:
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"-----Attempt {attempt + 1}/{max_retries} | Sending to {evaluation_url}-----")
                
                response = await client.post(
                    evaluation_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Success case
                if response.status_code == 200:
                    logger.info(
                        f"Evaluation submitted successfully | "
                        f"Email={payload.get('email')} | Round={payload.get('round')} | "
                        f"URL={evaluation_url}"
                    )
                    logger.info(f"Response: {response.text}")
                    logger.info("=====Payload That Sent Successfully on{evaluation_url}=====\n{payload}\n===============")
                    return True
                
                # Non-200 response
                logger.warning(
                    f"Evaluation returned {response.status_code} | "
                    f"Attempt {attempt + 1}/{max_retries} | "
                    f"Response: {response.text[:200]}"
                )
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout on attempt {attempt + 1}/{max_retries} | Error: {e}")
        except httpx.NetworkError as e:
            logger.error(f"Network error on attempt {attempt + 1}/{max_retries} | Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries} | Error: {e}", exc_info=True)
        
        # Exponential backoff with cap at 16 seconds
        if attempt < max_retries - 1:
            delay = min(2 ** attempt, 16)
            logger.info(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
    
    # All retries exhausted
    logger.error(
        f"Failed to send evaluation after {max_retries} attempts | "
        f"Email={payload.get('email')} | Round={payload.get('round')} | "
        f"URL={evaluation_url}"
    )
    logger.info(f"=====Final payload that failed=====\n{payload}\n===============")
    
    return False
