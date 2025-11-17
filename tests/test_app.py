"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""

    def test_get_activities_returns_all_activities(self):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify structure of activities
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_activities_contain_expected_activities(self):
        """Test that specific activities are present"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Soccer Team",
            "Swimming Club",
            "Drama Club",
            "Orchestra",
            "Debate Team",
            "Science Club"
        ]
        
        for activity in expected_activities:
            assert activity in data


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@example.com"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@example.com" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_participant_to_activity(self):
        """Test that signup actually adds the participant to the activity"""
        # Get initial participant count
        response = client.get("/activities")
        initial_participants = response.json()["Chess Club"]["participants"].copy()
        
        # Sign up a new participant
        email = "newsignup@example.com"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        updated_participants = response.json()["Chess Club"]["participants"]
        
        assert email in updated_participants
        assert len(updated_participants) == len(initial_participants) + 1

    def test_signup_for_nonexistent_activity_returns_404(self):
        """Test that signup for nonexistent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@example.com"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_duplicate_signup_returns_400(self):
        """Test that duplicate signup returns 400 error"""
        email = "duplicate@example.com"
        activity = "Programming Class"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        
        data = response2.json()
        assert "already signed up" in data["detail"]

    def test_signup_with_multiple_emails(self):
        """Test that multiple different emails can signup for same activity"""
        activity = "Swimming Club"
        emails = ["swimmer1@example.com", "swimmer2@example.com", "swimmer3@example.com"]
        
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are in the activity
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        
        for email in emails:
            assert email in participants


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister endpoint"""

    def test_unregister_from_activity_success(self):
        """Test successful unregister from an activity"""
        email = "unregister@example.com"
        activity = "Drama Club"
        
        # First signup
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Then unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]

    def test_unregister_removes_participant(self):
        """Test that unregister actually removes the participant"""
        email = "removetest@example.com"
        activity = "Orchestra"
        
        # Signup
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Verify participant is there
        response = client.get("/activities")
        participants_before = response.json()[activity]["participants"]
        assert email in participants_before
        
        # Unregister
        client.delete(f"/activities/{activity}/unregister?email={email}")
        
        # Verify participant is removed
        response = client.get("/activities")
        participants_after = response.json()[activity]["participants"]
        assert email not in participants_after
        assert len(participants_after) == len(participants_before) - 1

    def test_unregister_from_nonexistent_activity_returns_404(self):
        """Test that unregister from nonexistent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@example.com"
        )
        assert response.status_code == 404

    def test_unregister_unregistered_participant_returns_400(self):
        """Test that unregistering a non-registered participant returns 400"""
        response = client.delete(
            "/activities/Debate Team/unregister?email=notregistered@example.com"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "not registered" in data["detail"]


class TestActivityAvailability:
    """Tests for activity availability (spots left)"""

    def test_availability_decreases_after_signup(self):
        """Test that available spots decrease after signup"""
        activity = "Gym Class"
        email = "availtest@example.com"
        
        response = client.get("/activities")
        initial_spots = (
            response.json()[activity]["max_participants"] - 
            len(response.json()[activity]["participants"])
        )
        
        client.post(f"/activities/{activity}/signup?email={email}")
        
        response = client.get("/activities")
        updated_spots = (
            response.json()[activity]["max_participants"] - 
            len(response.json()[activity]["participants"])
        )
        
        assert updated_spots == initial_spots - 1

    def test_availability_increases_after_unregister(self):
        """Test that available spots increase after unregister"""
        activity = "Soccer Team"
        email = "availtest2@example.com"
        
        # Signup
        client.post(f"/activities/{activity}/signup?email={email}")
        
        response = client.get("/activities")
        spots_after_signup = (
            response.json()[activity]["max_participants"] - 
            len(response.json()[activity]["participants"])
        )
        
        # Unregister
        client.delete(f"/activities/{activity}/unregister?email={email}")
        
        response = client.get("/activities")
        spots_after_unregister = (
            response.json()[activity]["max_participants"] - 
            len(response.json()[activity]["participants"])
        )
        
        assert spots_after_unregister == spots_after_signup + 1
