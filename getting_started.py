#!/usr/bin/env python3
"""
Getting Started with Botted Library
This is your first real usage example - not a demo or test.
"""

from botted_library import create_worker

def main():
    print("🚀 Welcome to Botted Library!")
    print("Let's create your first AI worker and give it a real task.\n")
    
    # Create your first worker
    print("Creating a planner worker...")
    my_assistant = create_worker("my_assistant", "planner")
    
    print("\n" + "="*60)
    print("🎯 REAL TASK EXAMPLE")
    print("="*60)
    
    # Give it a real task
    result = my_assistant.call(
        "Create a detailed plan for learning Python programming from scratch",
        timeline="3 months",
        skill_level="beginner",
        goal="become job-ready"
    )
    
    print("\n" + "="*60)
    print("📋 YOUR RESULTS")
    print("="*60)
    
    # Show what you got
    print(f"Task completed: {result['success']}")
    print(f"Summary: {result['summary']}")
    
    # Access the actual deliverables
    if 'deliverables' in result:
        deliverables = result['deliverables']
        
        if 'plan' in deliverables:
            print(f"\n📋 Your Learning Plan:")
            print(deliverables['plan'])
        
        if 'research' in deliverables:
            research = deliverables['research']
            print(f"\n🔍 Research Found {research['total_found']} resources:")
            for i, res in enumerate(research['results'][:5], 1):
                print(f"  {i}. {res.get('title', 'Resource')}")
    
    # Show next steps
    if result.get('next_steps'):
        print(f"\n🚀 Suggested Next Steps:")
        for i, step in enumerate(result['next_steps'], 1):
            print(f"  {i}. {step}")
    
    print("\n" + "="*60)
    print("🎉 CONGRATULATIONS!")
    print("="*60)
    print("You just used AI to create a personalized learning plan!")
    print("The worker analyzed your requirements, researched resources,")
    print("and created a structured plan tailored to your goals.")
    
    print("\n💡 What you can do next:")
    print("1. Try different worker roles: 'researcher', 'coder', 'editor'")
    print("2. Give more complex tasks with specific parameters")
    print("3. Use the results in your real projects")
    
    # Clean shutdown
    my_assistant.shutdown()
    print("\n✅ Session complete!")

if __name__ == "__main__":
    main()