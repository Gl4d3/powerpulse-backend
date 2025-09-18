"""
End-to-End PowerPulse Pipeline Test
Tests the complete workflow from upload to CSI calculation using real conversation data.
"""

import requests
import json
import time
import os
from pathlib import Path

class PowerPulseE2ETest:
    """End-to-end test using real conversation data."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        
    def load_real_conversation_data(self, file_path: str) -> dict:
        """Load the real conversation data from the JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def convert_to_powerpulse_format(self, raw_data: dict) -> list:
        """Convert the raw conversation data to PowerPulse format."""
        conversations = []
        
        for chat_id, messages in raw_data.items():
            # Group messages by conversation
            conversation = {
                "conversation_id": chat_id,
                "messages": []
            }
            
            for msg in messages:
                if msg.get("MESSAGE_CONTENT"):  # Skip null messages
                    message = {
                        "role": "user" if msg["DIRECTION"] == "to_company" else "assistant",
                        "content": msg["MESSAGE_CONTENT"],
                        "timestamp": msg["SOCIAL_CREATE_TIME"],
                        "platform": msg["PLATFORM"],
                        "agent_email": msg.get("AGENT_EMAIL"),
                        "message_id": msg["UNIQUE_POST_ID"]
                    }
                    conversation["messages"].append(message)
            
            if conversation["messages"]:  # Only add non-empty conversations
                conversations.append(conversation)
        
        return conversations
    
    def test_upload_real_data(self, data_file_path: str) -> dict:
        """Test uploading the real conversation data."""
        print("🚀 STARTING END-TO-END POWERPULSE TEST")
        print("=" * 60)
        
        # Load and convert data
        print("📂 Loading real conversation data...")
        raw_data = self.load_real_conversation_data(data_file_path)
        conversations = self.convert_to_powerpulse_format(raw_data)
        
        print(f"✅ Loaded {len(conversations)} conversations")
        print(f"✅ Total messages: {sum(len(conv['messages']) for conv in conversations)}")
        
        # Create temporary file with converted data
        temp_file = "temp_powerpulse_test.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2)
        
        try:
            # Upload the file
            print(f"\n📤 Uploading to {self.base_url}/api/interaction/upload-json-enhanced...")
            
            with open(temp_file, 'rb') as f:
                files = {'file': ('real_conversation_test.json', f, 'application/json')}
                data = {
                    'batch_strategy': 'auto',
                    'priority': 'high'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/interaction/upload-json-enhanced",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            print(f"📊 Upload Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get('session_id')
                
                print(f"✅ Session Created: {self.session_id}")
                print(f"✅ Status: {result.get('status')}")
                print(f"✅ Batch Strategy: {result.get('batch_strategy')}")
                print(f"✅ Estimated Cost Savings: {result.get('estimated_cost_savings')}%")
                print(f"✅ Processing Mode: {result.get('processing_mode', 'standard')}")
                
                return result
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"❌ Error: {response.text}")
                return {"error": response.text}
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def monitor_processing_status(self) -> dict:
        """Monitor the processing status until completion."""
        if not self.session_id:
            print("❌ No session ID available for monitoring")
            return {"error": "No session ID"}
        
        print(f"\n📊 MONITORING SESSION: {self.session_id}")
        print("-" * 40)
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = requests.get(
                    f"{self.base_url}/api/interaction/upload-status/{self.session_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    
                    print(f"[{attempt+1:2d}/30] Status: {status_data.get('status', 'unknown'):<12} "
                          f"Progress: {status_data.get('progress_percentage', 0):5.1f}% "
                          f"Processed: {status_data.get('processed_interactions', 0)}"
                          f"/{status_data.get('interactions_count', 0)}")
                    
                    # Check if processing is complete
                    status = status_data.get('status', '')
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n🎯 Processing {status.upper()}!")
                        return status_data
                    
                elif response.status_code == 404:
                    print(f"[{attempt+1:2d}/30] Session not found yet, waiting...")
                else:
                    print(f"[{attempt+1:2d}/30] Status check failed: {response.status_code}")
                
                time.sleep(2)  # Wait 2 seconds between checks
                attempt += 1
                
            except Exception as e:
                print(f"[{attempt+1:2d}/30] Error checking status: {e}")
                attempt += 1
                time.sleep(2)
        
        print("⚠️ Monitoring timeout reached")
        return {"status": "timeout"}
    
    def check_constitutional_compliance(self) -> dict:
        """Check constitutional compliance for the session."""
        if not self.session_id:
            print("❌ No session ID available for compliance check")
            return {"error": "No session ID"}
        
        print(f"\n⚖️ CONSTITUTIONAL COMPLIANCE CHECK")
        print("-" * 40)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/constitutional/compliance?session_id={self.session_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                compliance_data = response.json()
                
                print(f"✅ Overall Compliance: {compliance_data.get('is_compliant', 'Unknown')}")
                
                if 'constitutional_requirements' in compliance_data:
                    reqs = compliance_data['constitutional_requirements']
                    
                    # AI Supremacy
                    ai_supremacy = reqs.get('ai_supremacy', {})
                    print(f"🤖 AI Micro-Metrics Supremacy: {ai_supremacy.get('status', 'unknown')}")
                    
                    # Dual CSI Architecture
                    dual_csi = reqs.get('dual_csi_architecture', {})
                    print(f"🎯 Dual CSI Architecture: {dual_csi.get('status', 'unknown')}")
                    
                    # Cost Reduction
                    cost_reduction = reqs.get('cost_reduction', {})
                    print(f"💰 Cost Reduction (80%+): {cost_reduction.get('status', 'unknown')}")
                    
                    # Processing Speed
                    processing_speed = reqs.get('processing_speed', {})
                    print(f"⚡ Processing Speed (3-4/sec): {processing_speed.get('status', 'unknown')}")
                
                if compliance_data.get('violations'):
                    print(f"\n⚠️ Violations Found: {len(compliance_data['violations'])}")
                    for i, violation in enumerate(compliance_data['violations'][:3], 1):
                        print(f"  {i}. {violation}")
                
                return compliance_data
            else:
                print(f"❌ Compliance check failed: {response.status_code}")
                print(f"❌ Error: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ Exception during compliance check: {e}")
            return {"error": str(e)}
    
    def get_batch_configuration(self) -> dict:
        """Get current batch processing configuration."""
        print(f"\n⚙️ BATCH PROCESSING CONFIGURATION")
        print("-" * 40)
        
        try:
            response = requests.get(f"{self.base_url}/api/batch-config", timeout=10)
            
            if response.status_code == 200:
                config_data = response.json()
                
                if 'batch_settings' in config_data:
                    batch_settings = config_data['batch_settings']
                    print(f"✅ Batch Processing: {'Enabled' if batch_settings.get('enabled') else 'Disabled'}")
                    print(f"✅ Max Concurrent Sessions: {batch_settings.get('max_concurrent_sessions', 'N/A')}")
                
                if 'performance_metrics' in config_data:
                    metrics = config_data['performance_metrics']
                    print(f"🎯 Target Cost Reduction: {metrics.get('target_cost_reduction', 'N/A')}%")
                    print(f"🎯 Target Processing Speed: {metrics.get('target_processing_speed', 'N/A')} interactions/sec")
                
                if 'system_status' in config_data:
                    system_status = config_data['system_status']
                    print(f"📊 System Status: {system_status.get('status', 'unknown')}")
                
                return config_data
            else:
                print(f"❌ Config check failed: {response.status_code}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ Exception during config check: {e}")
            return {"error": str(e)}
    
    def run_complete_test(self, data_file_path: str) -> dict:
        """Run the complete end-to-end test."""
        results = {}
        
        # Step 1: Upload data
        upload_result = self.test_upload_real_data(data_file_path)
        results['upload'] = upload_result
        
        if 'error' in upload_result:
            return results
        
        # Step 2: Get batch configuration
        config_result = self.get_batch_configuration()
        results['batch_config'] = config_result
        
        # Step 3: Monitor processing
        status_result = self.monitor_processing_status()
        results['processing'] = status_result
        
        # Step 4: Check constitutional compliance
        compliance_result = self.check_constitutional_compliance()
        results['compliance'] = compliance_result
        
        # Final summary
        print(f"\n🏁 END-TO-END TEST SUMMARY")
        print("=" * 60)
        
        upload_success = 'error' not in upload_result
        processing_success = status_result.get('status') == 'completed'
        compliance_success = compliance_result.get('is_compliant', False)
        
        print(f"📤 Upload Success: {'✅' if upload_success else '❌'}")
        print(f"⚙️ Processing Success: {'✅' if processing_success else '❌'}")
        print(f"⚖️ Constitutional Compliance: {'✅' if compliance_success else '❌'}")
        
        overall_success = upload_success and processing_success and compliance_success
        print(f"\n🎯 OVERALL SUCCESS: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        results['overall_success'] = overall_success
        return results


def main():
    """Main function to run the end-to-end test."""
    print("🚨 PowerPulse End-to-End Pipeline Test")
    print("Using real conversation data from Kenya Power customer service")
    
    # Path to the real conversation data
    data_file = "attached_assets/snippet_1755240593792.json"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return False
    
    # Run the test
    tester = PowerPulseE2ETest()
    results = tester.run_complete_test(data_file)
    
    return results.get('overall_success', False)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)