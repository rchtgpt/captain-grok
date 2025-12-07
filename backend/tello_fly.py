"""
DJI Tello Drone - Fly Up and Down Script with Live Video Feed
Make sure you're connected to the Tello's WiFi network before running!
"""

from djitellopy import Tello
import cv2
import time
import threading


class TelloFlight:
    def __init__(self):
        self.tello = Tello()
        self.flying = False
        self.flight_done = False
    
    def flight_sequence(self):
        """Execute the flight sequence in background thread"""
        try:
            time.sleep(1)  # Let video stabilize first
            
            # Take off
            print("Taking off...")
            self.tello.takeoff()
            time.sleep(2)  # Stabilize after takeoff
            
            # Fly up 50cm
            print("Flying up...")
            self.tello.move_up(50)
            time.sleep(1)
            
            # Fly down 50cm (back to original height)
            print("Flying down...")
            self.tello.move_down(50)
            time.sleep(1)
            
            # Land
            print("Landing...")
            self.tello.land()
            print("Flight complete!")
            
        except Exception as e:
            print(f"Flight error: {e}")
            try:
                self.tello.land()
            except:
                pass
        
        finally:
            self.flight_done = True
    
    def run(self):
        """Main function - video on main thread, flight on background thread"""
        try:
            # Connect to the drone
            print("Connecting to Tello...")
            self.tello.connect()
            
            # Check battery level
            battery = self.tello.get_battery()
            print(f"Battery level: {battery}%")
            
            if battery < 20:
                print("Warning: Battery is low! Please charge before flying.")
                return
            
            # Start video stream
            print("Starting video stream...")
            self.tello.streamon()
            time.sleep(2)  # Give camera time to initialize
            
            # Start flight sequence in background thread
            flight_thread = threading.Thread(target=self.flight_sequence)
            flight_thread.start()
            
            # Video display loop on main thread (required for macOS)
            print("Video streaming... Press 'q' to quit")
            while not self.flight_done:
                frame = self.tello.get_frame_read().frame
                if frame is not None:
                    # Resize for better display
                    frame = cv2.resize(frame, (960, 720))
                    
                    # Add battery info overlay
                    battery = self.tello.get_battery()
                    cv2.putText(frame, f"Battery: {battery}%", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Show the frame
                    cv2.imshow("Tello Camera", frame)
                
                # Press 'q' to quit early
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # Keep showing video for a moment after flight ends
            end_time = time.time() + 3
            while time.time() < end_time:
                frame = self.tello.get_frame_read().frame
                if frame is not None:
                    frame = cv2.resize(frame, (960, 720))
                    cv2.imshow("Tello Camera", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            flight_thread.join()
            
        except Exception as e:
            print(f"Error: {e}")
            try:
                self.tello.land()
            except:
                pass
        
        finally:
            cv2.destroyAllWindows()
            self.tello.streamoff()
            self.tello.end()


def main():
    flight = TelloFlight()
    flight.run()


if __name__ == "__main__":
    main()
