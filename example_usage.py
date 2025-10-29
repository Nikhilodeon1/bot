#!/usr/bin/env python3
"""
Example usage of the human-like AI workers
"""

from botted_library import create_worker
import os

# Load environment variables
def load_env():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Configuration for all workers
config = {
    'llm': {
        'provider': 'gemini',
        'api_key': os.getenv('GEMINI_API_KEY')
    },
    'browser': {'type': 'chrome'}
}

# Example 1: Marketing Manager
sarah = create_worker(
    name="Sarah",
    role="Marketing Manager",
    job_description="Specializes in market research, competitive analysis, and content strategy. Expert at finding trends and creating actionable marketing insights.",
    config=config
)

# Example 2: Software Developer  
alex = create_worker(
    name="Alex",
    role="Software Developer",
    job_description="Full-stack developer with expertise in Python, JavaScript, and web technologies. Specializes in building scalable applications and writing clean, maintainable code.",
    config=config
)

# Example 3: Data Analyst
maya = create_worker(
    name="Maya", 
    role="Data Analyst",
    job_description="Expert in data analysis, statistical modeling, and business intelligence. Specializes in extracting insights from complex datasets and creating comprehensive reports.",
    config=config
)

# Example 4: Content Writer
jordan = create_worker(
    name="Jordan",
    role="Content Writer", 
    job_description="Professional writer specializing in technical documentation, blog posts, and marketing content. Expert at making complex topics accessible and engaging.",
    config=config
)

def demo_workers():
    """Demonstrate different workers doing tasks suited to their roles"""
    
    print("🎯 DEMO: Human-like AI Workers")
    print("=" * 50)
    
    # Marketing Manager doing market research
    print("\n📊 Sarah (Marketing Manager) - Market Research")
    result1 = sarah.call("Research the top 3 competitors in the AI chatbot space and analyze their pricing strategies")
    print(f"✅ Completed in {result1.get('execution_time', 0):.1f}s")
    
    # Software Developer building something
    print("\n💻 Alex (Software Developer) - Code Development")  
    result2 = alex.call("Create a Python function that validates email addresses using regex and includes proper error handling")
    print(f"✅ Completed in {result2.get('execution_time', 0):.1f}s")
    
    # Data Analyst processing information
    print("\n📈 Maya (Data Analyst) - Data Analysis")
    result3 = maya.call("Research current AI adoption rates in different industries and create a summary report")
    print(f"✅ Completed in {result3.get('execution_time', 0):.1f}s")
    
    # Content Writer creating content
    print("\n✍️ Jordan (Content Writer) - Content Creation")
    result4 = jordan.call("Write a blog post about the benefits of AI automation for small businesses")
    print(f"✅ Completed in {result4.get('execution_time', 0):.1f}s")
    
    print("\n🎉 All workers completed their tasks!")
    print("Each worker used the tools they needed (web search, coding, document creation, etc.)")

if __name__ == "__main__":
    demo_workers()