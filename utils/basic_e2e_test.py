"""
Basic End-to-End PowerPulse Pipeline Test using working endpoints
Tests the complete workflow using the basic upload endpoint that we know works.
"""

import requests
import json
import time
import os

class BasicPowerPulseE2ETest:
    """Basic end-to-end test using working upload endpoint."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.upload_id = None
        
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
        
        # Limit to first 3 conversations for testing
        return conversations[:3]
    
    def test_basic_upload(self, data_file_path: str) -> dict:
        """Test uploading using the basic working endpoint."""
        print("🚀 STARTING BASIC POWERPULSE PIPELINE TEST")
        print("=" * 60)
        
        # Load and convert data
        print("📂 Loading real conversation data...")
        raw_data = self.load_real_conversation_data(data_file_path)
        conversations = self.convert_to_powerpulse_format(raw_data)
        
        print(f"✅ Loaded {len(conversations)} conversations (limited for testing)")
        print(f"✅ Total messages: {sum(len(conv['messages']) for conv in conversations)}")
        
        # Create temporary file with converted data
        temp_file = "temp_basic_test.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2)
        
        try:
            # Upload the file using basic endpoint
            print(f"\n📤 Uploading to {self.base_url}/api/interaction/upload-json...")
            
            with open(temp_file, 'rb') as f:
                files = {'file': ('basic_test.json', f, 'application/json')}
                
                response = requests.post(
                    f"{self.base_url}/api/interaction/upload-json",
                    files=files,
                    timeout=30
                )
            
            print(f"📊 Upload Response Status: {response.status_code}")
            
            if response.status_code == 202:
                result = response.json()
                self.upload_id = result.get('upload_id')
                
                print(f"✅ Upload ID: {self.upload_id}")
                print(f"✅ Status: {result.get('success')}")
                print(f"✅ Message: {result.get('message')}")
                print(f"✅ Conversations Processed: {result.get('conversations_processed', 0)}")
                print(f"✅ Messages Processed: {result.get('messages_processed', 0)}")
                
                return result
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"❌ Error: {response.text}")
                return {"error": response.text}
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def check_conversations_created(self) -> dict:
        """Check if conversations were created in the system."""
        print(f"\n📊 CHECKING CONVERSATIONS IN SYSTEM")
        print("-" * 40)
        
        try:
            # Get conversations
            response = requests.get(f"{self.base_url}/api/conversations", timeout=10)
            
            if response.status_code == 200:
                conversations_data = response.json()
                
                total_conversations = conversations_data.get('total', 0)
                conversations = conversations_data.get('conversations', [])
                
                print(f"✅ Total Conversations in System: {total_conversations}")
                
                if conversations:
                    print("✅ Recent Conversations:")
                    for i, conv in enumerate(conversations[:3], 1):
                        print(f"  {i}. ID: {conv.get('id')} | Messages: {conv.get('message_count', 0)}")
                
                return conversations_data
            else:
                print(f"❌ Failed to get conversations: {response.status_code}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return {"error": str(e)}
    
    def check_interaction_analysis(self) -> dict:
        """Check if interaction analysis was performed."""
        print(f"\n🔬 CHECKING INTERACTION ANALYSIS")
        print("-" * 40)
        
        try:
            # Get interaction metrics
            response = requests.get(f"{self.base_url}/api/interactions/metrics", timeout=10)
            
            if response.status_code == 200:
                metrics_data = response.json()
                
                print(f"✅ Interaction Analysis Available")
                
                if 'summary' in metrics_data:
                    summary = metrics_data['summary']
                    print(f"✅ Total Interactions: {summary.get('total_interactions', 0)}")
                    print(f"✅ Average CSI Score: {summary.get('avg_csi_score', 'N/A')}")
                
                return metrics_data
            else:
                print(f"❌ Failed to get interaction metrics: {response.status_code}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return {"error": str(e)}
    
    def check_csi_calculation(self) -> dict:
        """Check if CSI scores were calculated."""
        print(f"\n📈 CHECKING CSI CALCULATION")
        print("-" * 40)
        
        try:
            # Get recent interactions with CSI scores
            response = requests.get(f"{self.base_url}/api/interactions", timeout=10)
            
            if response.status_code == 200:
                interactions_data = response.json()
                
                interactions = interactions_data.get('interactions', [])
                
                if interactions:
                    csi_scores = []
                    for interaction in interactions[:5]:
                        csi_score = interaction.get('csi_score')
                        if csi_score is not None:
                            csi_scores.append(csi_score)
                    
                    if csi_scores:
                        avg_csi = sum(csi_scores) / len(csi_scores)
                        print(f"✅ CSI Scores Found: {len(csi_scores)} interactions")
                        print(f"✅ Average CSI: {avg_csi:.2f}")
                        print(f"✅ CSI Range: {min(csi_scores):.2f} - {max(csi_scores):.2f}")
                        
                        # Check constitutional compliance (CSI > 0.75)
                        compliant_scores = [s for s in csi_scores if s > 0.75]
                        compliance_rate = len(compliant_scores) / len(csi_scores) * 100
                        print(f"✅ Constitutional Compliance: {compliance_rate:.1f}% (CSI > 0.75)")
                        
                        return {
                            "csi_calculated": True,
                            "average_csi": avg_csi,
                            "compliance_rate": compliance_rate,
                            "total_scored": len(csi_scores)
                        }
                    else:
                        print("⚠️ No CSI scores found yet")
                        return {"csi_calculated": False, "reason": "No CSI scores"}
                else:
                    print("⚠️ No interactions found")
                    return {"csi_calculated": False, "reason": "No interactions"}
                
            else:
                print(f"❌ Failed to get interactions: {response.status_code}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return {"error": str(e)}
    
    def run_basic_pipeline_test(self, data_file_path: str) -> dict:
        """Run the basic end-to-end pipeline test."""
        results = {}
        
        # Step 1: Upload data
        upload_result = self.test_basic_upload(data_file_path)
        results['upload'] = upload_result
        
        if 'error' in upload_result:
            return results
        
        # Wait a moment for processing
        print("\n⏳ Waiting for processing...")
        time.sleep(3)
        
        # Step 2: Check conversations
        conversations_result = self.check_conversations_created()
        results['conversations'] = conversations_result
        
        # Step 3: Check interaction analysis  
        analysis_result = self.check_interaction_analysis()
        results['analysis'] = analysis_result
        
        # Step 4: Check CSI calculation
        csi_result = self.check_csi_calculation()
        results['csi'] = csi_result
        
        # Final summary
        print(f"\n🏁 BASIC PIPELINE TEST SUMMARY")
        print("=" * 60)
        
        upload_success = 'error' not in upload_result
        conversations_success = 'error' not in conversations_result
        analysis_success = 'error' not in analysis_result  
        csi_success = csi_result.get('csi_calculated', False)
        
        print(f"📤 Upload Success: {'✅' if upload_success else '❌'}")
        print(f"💬 Conversations Created: {'✅' if conversations_success else '❌'}")
        print(f"🔬 Analysis Performed: {'✅' if analysis_success else '❌'}")
        print(f"📈 CSI Calculated: {'✅' if csi_success else '❌'}")
        
        overall_success = upload_success and conversations_success and analysis_success and csi_success
        print(f"\n🎯 OVERALL PIPELINE SUCCESS: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        if csi_success:
            avg_csi = csi_result.get('average_csi', 0)
            compliance = csi_result.get('compliance_rate', 0)
            print(f"📊 Average CSI Score: {avg_csi:.2f}")
            print(f"⚖️ Constitutional Compliance Rate: {compliance:.1f}%")
        
        results['overall_success'] = overall_success
        return results


def main():
    """Main function to run the basic pipeline test."""
    print("🚨 PowerPulse Basic End-to-End Pipeline Test")
    print("Using real conversation data from Kenya Power customer service")
    
    # Path to the real conversation data
    data_file = "attached_assets/snippet_1755240593792.json"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return False
    
    # Run the test
    tester = BasicPowerPulseE2ETest()
    results = tester.run_basic_pipeline_test(data_file)
    
    return results.get('overall_success', False)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)