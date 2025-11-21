#!/usr/bin/env python3
"""
Performance Analysis Script for StockBuddy

Analyzes backend logs to identify performance bottlenecks.
Extracts timing information from performance logs and generates a report.

Usage:
    python scripts/analyze_performance.py [log_file]
    
    If no log_file is provided, uses the latest log from /tmp/stockbuddy_logs_*
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class PerformanceAnalyzer:
    """Analyze performance logs and generate reports."""
    
    def __init__(self):
        self.events = []
        self.conversations = defaultdict(dict)
        
    def parse_log_file(self, log_file: Path):
        """Parse log file and extract performance events."""
        print(f"\n📊 Analyzing log file: {log_file}")
        print("=" * 80)
        
        # Pattern to match performance logs
        perf_pattern = r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3}).*⏱️\s\[PERF\]\s(.+)'
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(perf_pattern, line)
                if match:
                    timestamp_str, message = match.groups()
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    self.events.append({
                        'timestamp': timestamp,
                        'message': message
                    })
        
        print(f"✅ Found {len(self.events)} performance events\n")
        
    def analyze_conversations(self):
        """Group events by conversation and calculate durations."""
        conv_pattern = r'conversation:\s(conv-[a-f0-9-]+)'
        
        for event in self.events:
            msg = event['message']
            match = re.search(conv_pattern, msg)
            if match:
                conv_id = match.group(1)
                
                # Extract phase (Super Agent, Planner, Task)
                if 'Super Agent started' in msg:
                    self.conversations[conv_id]['super_agent_start'] = event['timestamp']
                elif 'Super Agent completed' in msg:
                    self.conversations[conv_id]['super_agent_end'] = event['timestamp']
                    # Extract duration from message
                    duration_match = re.search(r'in\s([\d.]+)s', msg)
                    if duration_match:
                        self.conversations[conv_id]['super_agent_duration'] = float(duration_match.group(1))
                elif 'Planner started' in msg:
                    self.conversations[conv_id]['planner_start'] = event['timestamp']
                elif 'Planner completed' in msg:
                    self.conversations[conv_id]['planner_end'] = event['timestamp']
                    duration_match = re.search(r'in\s([\d.]+)s', msg)
                    if duration_match:
                        self.conversations[conv_id]['planner_duration'] = float(duration_match.group(1))
                elif 'Task execution started' in msg:
                    if 'tasks' not in self.conversations[conv_id]:
                        self.conversations[conv_id]['tasks'] = []
                    agent_match = re.search(r'started:\s(\w+)', msg)
                    if agent_match:
                        agent_name = agent_match.group(1)
                        self.conversations[conv_id]['tasks'].append({
                            'agent': agent_name,
                            'start': event['timestamp']
                        })
                elif 'Task execution completed' in msg:
                    agent_match = re.search(r'completed:\s(\w+)', msg)
                    duration_match = re.search(r'Duration:\s([\d.]+)s', msg)
                    if agent_match and duration_match and 'tasks' in self.conversations[conv_id]:
                        agent_name = agent_match.group(1)
                        duration = float(duration_match.group(1))
                        # Find matching task
                        for task in self.conversations[conv_id]['tasks']:
                            if task['agent'] == agent_name and 'duration' not in task:
                                task['duration'] = duration
                                task['end'] = event['timestamp']
                                break
    
    def generate_report(self):
        """Generate performance analysis report."""
        if not self.conversations:
            print("⚠️  No conversation performance data found.")
            return
        
        print("\n" + "=" * 80)
        print("📈 PERFORMANCE ANALYSIS REPORT")
        print("=" * 80)
        
        total_super_agent = 0
        total_planner = 0
        total_tasks = 0
        task_count = 0
        
        for conv_id, data in self.conversations.items():
            print(f"\n🔹 Conversation: {conv_id[:20]}...")
            print("-" * 80)
            
            # Super Agent
            if 'super_agent_duration' in data:
                duration = data['super_agent_duration']
                total_super_agent += duration
                print(f"  Super Agent:   {duration:>8.2f}s")
            
            # Planner
            if 'planner_duration' in data:
                duration = data['planner_duration']
                total_planner += duration
                print(f"  Planner:       {duration:>8.2f}s")
            
            # Tasks
            if 'tasks' in data:
                print(f"  Tasks:")
                for i, task in enumerate(data['tasks'], 1):
                    if 'duration' in task:
                        duration = task['duration']
                        total_tasks += duration
                        task_count += 1
                        print(f"    {i}. {task['agent']:<20} {duration:>8.2f}s")
            
            # Total time for conversation
            total_conv_time = data.get('super_agent_duration', 0) + \
                             data.get('planner_duration', 0)
            if 'tasks' in data:
                total_conv_time += sum(t.get('duration', 0) for t in data['tasks'])
            print(f"\n  Total Time:    {total_conv_time:>8.2f}s")
        
        # Summary
        conv_count = len(self.conversations)
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total Conversations: {conv_count}")
        
        if conv_count > 0:
            print(f"\nAverage Times:")
            if total_super_agent > 0:
                print(f"  Super Agent:   {total_super_agent / conv_count:>8.2f}s")
            if total_planner > 0:
                print(f"  Planner:       {total_planner / conv_count:>8.2f}s")
            if task_count > 0:
                print(f"  Task (each):   {total_tasks / task_count:>8.2f}s")
        
        # Bottleneck analysis
        print("\n" + "=" * 80)
        print("🎯 BOTTLENECK ANALYSIS")
        print("=" * 80)
        
        if total_super_agent > 0:
            pct = (total_super_agent / (total_super_agent + total_planner + total_tasks)) * 100
            print(f"  Super Agent: {pct:>6.1f}% of total time")
            if pct > 30:
                print(f"    ⚠️  HIGH - Consider caching or optimizing routing logic")
        
        if total_planner > 0:
            pct = (total_planner / (total_super_agent + total_planner + total_tasks)) * 100
            print(f"  Planner:     {pct:>6.1f}% of total time")
            if pct > 30:
                print(f"    ⚠️  HIGH - Consider simplifying planning or using templates")
        
        if total_tasks > 0:
            pct = (total_tasks / (total_super_agent + total_planner + total_tasks)) * 100
            print(f"  Tasks:       {pct:>6.1f}% of total time")
            if pct > 50:
                print(f"    ✅ GOOD - Most time spent in actual task execution")
        
        print("\n" + "=" * 80)
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 80)
        
        if total_super_agent / conv_count > 5:
            print("• Super Agent is slow (>5s avg) - Consider:")
            print("  - Enable fast-path routing for complex queries")
            print("  - Use smaller/faster LLM models for routing decisions")
            print("  - Cache routing decisions for similar queries")
        
        if total_planner / conv_count > 10:
            print("• Planner is slow (>10s avg) - Consider:")
            print("  - Simplify prompts and reduce context size")
            print("  - Use template-based planning for common patterns")
            print("  - Optimize LLM calls")
        
        if task_count > 0 and total_tasks / task_count > 30:
            print("• Individual tasks are slow (>30s avg) - Consider:")
            print("  - Review agent tool performance")
            print("  - Check for slow external API calls")
            print("  - Optimize data fetching strategies")
        
        print("\n")


def find_latest_log():
    """Find the latest backend log file."""
    log_dirs = sorted(Path('/tmp').glob('stockbuddy_logs_*'), reverse=True)
    if not log_dirs:
        return None
    return log_dirs[0] / 'backend.log'


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        log_file = Path(sys.argv[1])
    else:
        log_file = find_latest_log()
        if not log_file:
            print("❌ No log files found in /tmp/stockbuddy_logs_*")
            print("\nUsage: python scripts/analyze_performance.py [log_file]")
            sys.exit(1)
    
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        sys.exit(1)
    
    analyzer = PerformanceAnalyzer()
    analyzer.parse_log_file(log_file)
    analyzer.analyze_conversations()
    analyzer.generate_report()


if __name__ == '__main__':
    main()

