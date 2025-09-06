import time
import asyncio
from typing import Dict, List
from collections import deque
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    timestamp: float
    input_tokens: int
    output_tokens: int


class AnthropicRateLimiter:
    """Rate limiter for Anthropic API to prevent exceeding token limits"""
    
    def __init__(
        self,
        max_input_tokens_per_minute: int = 25000,  # Set slightly below 30k limit for safety
        max_requests_per_minute: int = 50,  # Conservative request limit
        window_seconds: int = 60
    ):
        self.max_input_tokens_per_minute = max_input_tokens_per_minute
        self.max_requests_per_minute = max_requests_per_minute
        self.window_seconds = window_seconds
        
        # Track usage over time
        self.token_usage_history: deque = deque()
        self.request_timestamps: deque = deque()
        
    def _cleanup_old_usage(self):
        """Remove usage records older than the window"""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        # Clean up token usage
        while self.token_usage_history and self.token_usage_history[0].timestamp < cutoff_time:
            self.token_usage_history.popleft()
            
        # Clean up request timestamps
        while self.request_timestamps and self.request_timestamps[0] < cutoff_time:
            self.request_timestamps.popleft()
    
    def _get_current_usage(self) -> Dict[str, int]:
        """Get current token and request usage in the window"""
        self._cleanup_old_usage()
        
        total_input_tokens = sum(usage.input_tokens for usage in self.token_usage_history)
        total_output_tokens = sum(usage.output_tokens for usage in self.token_usage_history)
        total_requests = len(self.request_timestamps)
        
        return {
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'requests': total_requests
        }
    
    def estimate_image_tokens(self, image_size_bytes: int) -> int:
        """Estimate tokens needed for an image based on size"""
        # Rough estimation: larger images use more tokens
        # Based on Anthropic's documentation, images can use 1000-2000+ tokens
        base_tokens = 1500  # Base token cost for image processing
        size_factor = min(image_size_bytes / (1024 * 1024), 5.0)  # Scale by MB, cap at 5MB
        estimated_tokens = int(base_tokens * (1 + size_factor * 0.5))
        return min(estimated_tokens, 4000)  # Cap at reasonable maximum
    
    def estimate_prompt_tokens(self, prompt: str) -> int:
        """Estimate tokens in text prompt (rough approximation)"""
        # Rough estimation: ~4 characters per token on average
        return len(prompt) // 4
    
    def can_make_request(self, estimated_input_tokens: int) -> bool:
        """Check if a request can be made without exceeding limits"""
        current_usage = self._get_current_usage()
        
        # Check input token limit
        if current_usage['input_tokens'] + estimated_input_tokens > self.max_input_tokens_per_minute:
            return False
            
        # Check request limit
        if current_usage['requests'] >= self.max_requests_per_minute:
            return False
            
        return True
    
    def calculate_wait_time(self, estimated_input_tokens: int) -> float:
        """Calculate how long to wait before making a request"""
        current_usage = self._get_current_usage()
        
        # If we can make the request now, no wait needed
        if self.can_make_request(estimated_input_tokens):
            return 0.0
        
        # Calculate wait time based on when oldest usage will expire
        if not self.token_usage_history and not self.request_timestamps:
            return 0.0
            
        # Find the oldest timestamp that's causing us to exceed limits
        oldest_token_time = self.token_usage_history[0].timestamp if self.token_usage_history else float('inf')
        oldest_request_time = self.request_timestamps[0] if self.request_timestamps else float('inf')
        
        oldest_time = min(oldest_token_time, oldest_request_time)
        current_time = time.time()
        
        # Wait until the oldest usage expires plus a small buffer
        wait_time = max(0.0, (oldest_time + self.window_seconds) - current_time + 1.0)
        return wait_time
    
    async def wait_for_capacity(self, estimated_input_tokens: int):
        """Wait until there's capacity to make a request"""
        wait_time = self.calculate_wait_time(estimated_input_tokens)
        
        if wait_time > 0:
            logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds for API capacity")
            await asyncio.sleep(wait_time)
    
    def record_usage(self, input_tokens: int, output_tokens: int = 0):
        """Record actual token usage after making a request"""
        current_time = time.time()
        
        # Record token usage
        usage = TokenUsage(
            timestamp=current_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        self.token_usage_history.append(usage)
        
        # Record request timestamp
        self.request_timestamps.append(current_time)
        
        # Clean up old records
        self._cleanup_old_usage()
        
        logger.debug(f"Recorded API usage: {input_tokens} input tokens, {output_tokens} output tokens")
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        current_usage = self._get_current_usage()
        
        return {
            'current_input_tokens': current_usage['input_tokens'],
            'current_output_tokens': current_usage['output_tokens'],
            'current_requests': current_usage['requests'],
            'max_input_tokens_per_minute': self.max_input_tokens_per_minute,
            'max_requests_per_minute': self.max_requests_per_minute,
            'input_tokens_remaining': max(0, self.max_input_tokens_per_minute - current_usage['input_tokens']),
            'requests_remaining': max(0, self.max_requests_per_minute - current_usage['requests']),
        }