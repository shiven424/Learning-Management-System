import grpc
import time
import random
import os
import json
import threading
import logging
from concurrent import futures
from typing import List
from lms_pb2 import (
    VoteRequest, VoteResponse,
    AppendEntriesRequest, AppendEntriesResponse,
    LogEntry, LeaderInfo
)

from lms_pb2_grpc import RaftServiceServicer, add_RaftServiceServicer_to_server, RaftServiceStub
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PEER_NODES = [
    "lms_server_1:5000",  # Example: First node
    "lms_server_2:5000",  # Example: Second node
    "lms_server_3:5000"   # Example: Third node
]
PEER_NODES.remove(f"{os.getenv('SERVER_NAME', None)}:5000")
class RaftNode(RaftServiceServicer):
    def __init__(self):
        self.node_id = os.getenv('SERVER_NAME', None)
        self.node_address = f"{os.getenv('SERVER_NAME', None)}:5000"
        self.peers = PEER_NODES # List of peer addresses (host:port) of other nodes
        self.current_term = 0  # Current term of the node
        self.voted_for = None  # Node that this node voted for in the current term
        self.log_storage_path = "/app/logs/raft.log"
        self.log = self.load_log()  # Log entries for consistency
        self.commit_index = 0  # Index of the last committed log entry
        self.last_applied = 0  # Index of the last applied log entry
        logger.info(f"PEERS: - {os.getenv('SERVER_NAME', None)}:5000 =  {self.peers}")
        self.next_index = {peer: 0 for peer in self.peers}  # Next log index to send to each peer
        self.match_index = {peer: 0 for peer in self.peers}  # Highest log index known to be replicated on each peer
        self.role = "Follower"  # Role: Follower, Candidate, or Leader
        self.votes_received = 0  # Votes received during election


        # Set up election timeout and heartbeat timer
        self.heartbeat_interval = 5  # Send heartbeats every second as leader
        self.election_timeout = self._random_timeout()
        self.election_timer = threading.Timer(self.election_timeout, self.start_election)

        # Start the election timer for the follower
        self.election_timer.start()
        logger.info(f"Node {self.node_id} initialized as Follower")

    def is_leader(self) -> bool:
        """Check if the node is the leader."""
        return self.role == "Leader"

    def load_log(self) -> List[LogEntry]:
        """Load the log from disk."""
        if os.path.exists(self.log_storage_path):
            with open(self.log_storage_path, "r") as f:
                log_entries = []
                for line in f:
                    data = json.loads(line)
                    log_entry = LogEntry(term=data['term'], data=data['data'])  # Adjust if data type differs
                    log_entries.append(log_entry)
                return log_entries
        return []


    def log_entry_to_dict(self,log_entry: LogEntry) -> dict:
        return {
            'term': log_entry.term,
            'data': log_entry.data
        }

    def save_log(self):
        """Save the log to disk."""
        with open(self.log_storage_path, "w") as f:
            for entry in self.log:
                f.write(json.dumps(self.log_entry_to_dict(entry)) + "\n")

    def _random_timeout(self):
        """Generate a random election timeout to avoid split votes."""
        return random.uniform(self.heartbeat_interval + 1, 10)

    def start_election(self):
        """Start a new election if no leader heartbeat received."""
        self.role = "Candidate"
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = 1  # Vote for self

        logger.info(f"Node {self.node_id} started an election for term {self.current_term}")

        # Send RequestVote RPCs to all peers
        for peer in self.peers:
            threading.Thread(target=self.request_vote, args=(peer,)).start()

    def request_vote(self, peer: str):
        """Send RequestVote RPC to a peer."""
        stub = self._get_stub(peer)
        request = VoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=len(self.log) - 1,
            last_log_term=self.log[-1].term if self.log else 0
        )
        try:
            response = stub.RequestVote(request)
            self.handle_vote_response(response)
        except grpc.RpcError as e:
            logger.info(f"Failed to request vote from {peer}: {e}")

    def handle_vote_response(self, response: VoteResponse):
        """Handle the response of a vote request."""
        if response.vote_granted:
            self.votes_received += 1
            logger.info(f"Node {self.node_id} received a vote. Total votes: {self.votes_received}")

            if self.votes_received > len(self.peers) // 2:
                self.become_leader()

    def become_leader(self):
        """Become the leader and start sending heartbeats."""
        self.role = "Leader"
        logger.info(f"Node {self.node_id} became the Leader for term {self.current_term}")

        # Initialize nextIndex for all peers
        for peer in self.peers:
            self.next_index[peer] = len(self.log)

        # Start sending heartbeats
        threading.Thread(target=self.send_heartbeats).start()

    def send_heartbeats(self):
        """Send periodic heartbeats to followers."""
        while self.role == "Leader":
            for peer in self.peers:
                entries = []  # Heartbeats do not contain entries
                threading.Thread(target=self.append_entries, args=(peer, entries)).start()
            time.sleep(self.heartbeat_interval)

    def append_entries(self, peer: str, entries: List[LogEntry]):
        """Send AppendEntries RPC to a peer."""
        stub = self._get_stub(peer)
        prev_log_index = len(self.log) - 1 if self.log else -1
        request = AppendEntriesRequest(
            term=self.current_term,
            leader_id=self.node_id,
            prev_log_index=prev_log_index,
            prev_log_term=self.log[-1].term if self.log else 0,
            entries=entries,
            commit_index=self.commit_index
        )
        try:
            response = stub.AppendEntries(request)
            self.handle_append_response(response)
        except grpc.RpcError as e:
            logger.info(f"Failed to append entries to {peer}: {e}")

    def handle_append_response(self, response: AppendEntriesResponse):
        """Handle the response of an AppendEntries RPC."""
        if response.success:
            logger.info(f"Log entry replicated on node {response.node_id}")
        else:
            logger.info(f"AppendEntries failed on node {response.node_id}. Retrying...")

    def _get_stub(self, peer: str):
        """Get the gRPC stub for a peer."""
        channel = grpc.insecure_channel(peer)
        return RaftServiceStub(channel)

    def propose_log_entry(self, data) -> bool:
        """Propose a new log entry to be committed."""
        if self.role != "Leader":
            logger.info(f"Node {self.node_id} is not the leader and cannot propose log entry.")
            return False

        # Create a new log entry
        new_log_entry = LogEntry(term=self.current_term, data=data)
        self.log.append(new_log_entry)
        self.save_log()  # Save updated log

        # Send AppendEntries to followers
        votes_received = 1  # Count self as a vote
        for peer in self.peers:
            # Calculate missing log entries if peer log is too short
            if len(peer.log) < len(self.log):
                missing_entries = self.log[len(peer.log):]  # All missing entries for this peer
                response = self.append_entries(peer, missing_entries)
            else:
                response = self.append_entries(peer, [new_log_entry])  # Just the new log entry

            if response.success:
                votes_received += 1

        # Commit the log entry if a majority is reached
        if votes_received > len(self.peers) // 2:
            self.commit_index += 1  # Update commit index
            self.save_log()  # Save log after commit
            logger.info(f"Log entry committed by majority. Data: {data}")
            return True
        else:
            logger.info(f"Not enough votes to commit log entry. Votes received: {votes_received}")
            return False

    # RPC handlers for Raft protocol
    def RequestVote(self, request, context):
        """Handle RequestVote RPC from a candidate."""
        if (request.term > self.current_term or
                (request.term == self.current_term and self.voted_for in (None, request.candidate_id))):
            self.voted_for = request.candidate_id
            self.current_term = request.term
            self.election_timer.cancel()  # Reset election timer
            return VoteResponse(term=self.current_term, vote_granted=True)
        return VoteResponse(term=self.current_term, vote_granted=False)

    def AppendEntries(self, request, context):
        """
        Handle AppendEntries RPC from the leader. This includes both heartbeats and log replication.
        """
        logger.debug(f"Received AppendEntries request: {request}")

        # Reject if the leader's term is less than the current term
        if request.term < self.current_term:
            logger.warning(f"Rejected AppendEntries from leader with term {request.term}. "
                        f"Current term is {self.current_term}.")
            return AppendEntriesResponse(term=self.current_term, success=False, node_id=self.node_id)

        # Accept the leader's term and become a follower
        self.role = "Follower"
        self.current_term = request.term  # Update current term

        # Reset the election timer
        self.election_timer.cancel()
        self.election_timer = threading.Timer(self._random_timeout(), self.start_election)
        self.election_timer.start()

        # Check log consistency: Ensure log matches up to prev_log_index
        if (request.prev_log_index == -1 or
            (request.prev_log_index < len(self.log) and self.log[request.prev_log_index].term == request.prev_log_term)):
            
            # Log is consistent, append new entries
            logger.debug(f"Log consistency check passed for prev_log_index {request.prev_log_index}. Appending entries.")
            
            # Truncate the log at prev_log_index and append new entries
            self.log = self.log[:request.prev_log_index + 1] + list(request.entries)
            
            # Update commit index
            self.commit_index = min(request.commit_index, len(self.log) - 1)
            
            # Save updated log to disk
            self.save_log()

            logger.debug(f"Entries appended successfully. New log length: {len(self.log)}.")
            return AppendEntriesResponse(term=self.current_term, success=True, node_id=self.node_id)

        # Handle log inconsistency
        if request.prev_log_index >= len(self.log):
            logger.info(f"Log inconsistency: Follower's log is too short. "
                        f"Follower log length is {len(self.log)}, but received prev_log_index {request.prev_log_index}.")
        else:
            logger.info(f"Log inconsistency: Term mismatch at index {request.prev_log_index}. "
                        f"Follower's log term is {self.log[request.prev_log_index].term}, "
                        f"but leader's prev_log_term is {request.prev_log_term}.")
        
        # Log consistency check failed, request missing entries
        logger.warning(f"Log consistency check failed for prev_log_index {request.prev_log_index}. Rejecting AppendEntries.")
        
        return AppendEntriesResponse(term=self.current_term, success=False, node_id=self.node_id)


    def GetLeader(self, request, context):
        """Handle GetLeader RPC."""
        if self.role == "Leader":
            leader_address = self.node_address
        else:
            leader_address = ""

        return LeaderInfo(leader_address=leader_address)

# To run the server, create a function similar to the following:
def serve(peers: List[str]):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_node = RaftNode(peers)
    add_RaftServiceServicer_to_server(raft_node, server)
    server.add_insecure_port('[::]:50051')  # Bind to port (can be adjusted)
    server.start()
    logger.info("Raft server started...")
    server.wait_for_termination()

raft_service = RaftNode()
