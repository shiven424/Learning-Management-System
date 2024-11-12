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
    LogEntry, LeaderInfo, LastLogIndexResponse, Empty
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
        logger.info(f"[{self.role}] PEERS: - {os.getenv('SERVER_NAME', None)}:5000 =  {self.peers}")
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
        logger.info(f"[{self.role}] Node {self.node_id} initialized as Follower")

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

        logger.info(f"[{self.role}] Node {self.node_id} started an election for term {self.current_term}")

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
            logger.info(f"[{self.role}] Failed to request vote from {peer}: {e}")

    def handle_vote_response(self, response: VoteResponse):
        """Handle the response of a vote request."""
        if response.vote_granted:
            self.votes_received += 1
            logger.info(f"[{self.role}] Node {self.node_id} received a vote. Total votes: {self.votes_received}")

            if self.votes_received > len(self.peers) // 2:
                self.become_leader()

    def become_leader(self):
        """Become the leader and start sending heartbeats."""
        self.role = "Leader"
        logger.info(f"[{self.role}] Node {self.node_id} became the Leader for term {self.current_term}")

        # Initialize nextIndex for all peers
        for peer in self.peers:
            self.next_index[peer] = len(self.log)

        # Start sending heartbeats
        threading.Thread(target=self.send_heartbeats).start()

    def send_heartbeats(self):
        """Send periodic heartbeats to followers."""
        while self.role == "Leader":
            for peer in self.peers:
                # Get the index and term of the last log entry
                expected_index = len(self.log) - 1  # Last index in leader's log
                expected_term = self.log[expected_index].term if self.log else self.current_term  # Term of the last entry

                # Send AppendEntries RPC without new entries (heartbeat)
                threading.Thread(
                    target=self.append_entries,
                    args=(peer, [], expected_index, expected_term)
                ).start()

            time.sleep(self.heartbeat_interval)

    def append_entries(self, peer: str, entries: List[LogEntry], expected_index, expected_term):
        """Send AppendEntries RPC to a peer."""
        stub = self._get_stub(peer)
        logger.info(f"[{self.role}] Current logs are {self.log} and prev_log_index is {len(self.log) - 1 if self.log else -1}") 
        request = AppendEntriesRequest(
            term=self.current_term,
            leader_id=self.node_id,
            prev_log_index=expected_index,
            prev_log_term=expected_term,
            entries=entries,
            commit_index=self.commit_index
        )
        try:
            response = stub.AppendEntries(request)
            self.handle_append_response(response)
            return response
        except grpc.RpcError as e:
            logger.info(f"[{self.role}] Failed to append entries to {peer}: {e}")
            return None

    def handle_append_response(self, response: AppendEntriesResponse):
        """Handle the response of an AppendEntries RPC."""
        if response.success:
            logger.info(f"[{self.role}] Log entry replicated on node {response.node_id}")
        else:
            logger.info(f"[{self.role}] AppendEntries failed on node {response.node_id}. Retrying...")

    def _get_stub(self, peer: str):
        """Get the gRPC stub for a peer."""
        channel = grpc.insecure_channel(peer)
        return RaftServiceStub(channel)

    def propose_log_entry(self, data) -> bool:
        """Propose a new log entry to be committed."""
        if self.role != "Leader":
            logger.info(f"[{self.role}] Node {self.node_id} is not the leader and cannot propose log entry.")
            return False

        # Create a new log entry
        new_log_entry = LogEntry(term=self.current_term, data=data)
        self.log.append(new_log_entry)
        logger.info(f"[{self.role}] New log entry created and appended to log: {new_log_entry}")

        # Send AppendEntries to followers, including the newly appended entry
        votes_received = 1  # Count self as a vote
        for peer in self.peers:
            stub = self._get_stub(peer)
            logger.info(f"[{self.role}] Preparing to send AppendEntries to peer {peer}")

            # Get the last log index from the peer
            try:
                follower_response = stub.GetLastLogIndex(Empty())
                logger.info(f"[{self.role}] Received last log index from {peer}: {follower_response.last_log_index}")
            except grpc.RpcError as e:
                logger.error(f"Failed to get last log index from {peer}. Exception: {e}")
                continue

            if follower_response:
                # Case 1: Follower's log is outdated or has missing entries
                if follower_response.last_log_term < self.log[-1].term or follower_response.last_log_index < len(self.log) - 1:
                    logger.info(f"[{self.role}] Peer {peer} has an outdated log. Last log term: {follower_response.last_log_term}, index: {follower_response.last_log_index}")
                    
                    # Case 2: Handle log conflict (same index, different terms)
                    if follower_response.last_log_index!= -1 and follower_response.last_log_indexj < len(self.log) - 1 and self.log[follower_response.last_log_index].term != follower_response.last_log_term:
                        conflicting_entries = self.log[:follower_response.last_log_index]
                        logger.info(f"[{self.role}] Conflict at index {follower_response.last_log_index}. Term mismatch: {follower_response.last_log_term} != {self.log[follower_response.last_log_index].term}")
                        append_response = self.append_entries(peer, conflicting_entries, follower_response.last_log_index - 1, self.log[follower_response.last_log_index - 1].term)
                    else:
                        missing_entries = self.log[follower_response.last_log_index + 1:]
                        logger.info(f"[{self.role}] Sending missing log entries to {peer}: {missing_entries}")
                        append_response = self.append_entries(peer, missing_entries, follower_response.last_log_index, follower_response.last_log_term)
                
                elif follower_response.last_log_index >= len(self.log):
                    truncation_point = len(self.log) - 1
                    logger.info(f"[{self.role}] Follower log longer than leader's. Sending truncation command to {peer} at index {truncation_point}.")
                    append_response = self.append_entries(peer, [], truncation_point, self.log[truncation_point].term)
                
                else:
                    append_response = self.append_entries(peer, [new_log_entry], follower_response.last_log_index, follower_response.last_log_term)
                    logger.info(f"[{self.role}] Sending only new log entry to {peer}: {new_log_entry}")

                if append_response and append_response.success:
                    votes_received += 1
                    logger.info(f"[{self.role}] Peer {peer} successfully appended the log entry.")
                else:
                    logger.warning(f"Peer {peer} failed to append the log entry.")
            else:
                logger.warning(f"No response received from peer {peer} for log append request.")

        # Commit the log entry if a majority is reached
        if votes_received > len(self.peers) // 2:
            self.commit_index += 1
            self.save_log()
            logger.info(f"[{self.role}] Log entry committed with majority. Data: {data}, Votes received: {votes_received}")
            return True
        else:
            logger.warning(f"Not enough votes to commit log entry. Votes received: {votes_received}")
            return False

    # RPC handlers for Raft protocol
    def RequestVote(self, request, context):    ## log legth
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
        Handles incoming AppendEntries RPC from the leader to replicate logs and maintain consistency.
        """
        logger.info(f"[{self.role}] AppendEntries called by leader {request.leader_id} with term {request.term} and {len(request.entries)} entries.")

        # Step 1: Update term and role if needed (leader's term > follower's).
        if request.term > self.current_term:
            logger.info(f"[{self.role}] Leader term {request.term} is greater than current term {self.current_term}. Updating term and becoming Follower.")
            self.current_term = request.term
            self.role = "Follower"
            self.voted_for = None

        # Step 2: Reject if term is outdated (leader's term < follower's).
        if request.term < self.current_term:
            logger.warning(f"Rejecting AppendEntries due to outdated term {request.term}. Current term is {self.current_term}.")
            return AppendEntriesResponse(term=self.current_term, success=False, node_id=self.node_id)

        # Step 3: Reset election timer since valid AppendEntries was received from the leader.
        self.election_timer.cancel()
        logger.info("Election timer reset due to valid AppendEntries RPC.")

        # Step 4: Handle heartbeat with no log entries.
        if not request.entries:
            logger.info("Heartbeat received. No log entries to append.")
            self.commit_index = min(request.commit_index, len(self.log) - 1)
            logger.info(f"[{self.role}] Commit index updated to {self.commit_index} based on leader's commit index.")
            return AppendEntriesResponse(term=self.current_term, success=True, node_id=self.node_id)

        # Step 5: Check if prev_log_index is valid.
        if request.prev_log_index >= len(self.log):
            logger.info(f"[{self.role}] Log mismatch: Follower's log is shorter. Adding missing entries from index {request.prev_log_index}.")
            self.log += list(request.entries)
            self.commit_index = min(request.commit_index, len(self.log) - 1)
            return AppendEntriesResponse(term=self.current_term, success=True, node_id=self.node_id)

        # Step 6: Check for log conflict at prev_log_index (term mismatch).
        if self.log[request.prev_log_index].term != request.prev_log_term:
            logger.info(f"[{self.role}] Conflict at index {request.prev_log_index}: follower term {self.log[request.prev_log_index].term} vs leader term {request.prev_log_term}. Truncating log.")
            self.log = self.log[:request.prev_log_index + 1] + list(request.entries)
            self.commit_index = min(request.commit_index, len(self.log) - 1)
            return AppendEntriesResponse(term=self.current_term, success=True, node_id=self.node_id)

        # Step 7: No conflict, append new entries if needed.
        logger.info(f"[{self.role}] Appending {len(request.entries)} new entries to the log.")
        self.log = self.log[:request.prev_log_index + 1] + list(request.entries)

        # Step 8: Update the commit index.
        self.commit_index = min(request.commit_index, len(self.log) - 1)
        logger.info(f"[{self.role}] Commit index updated to {self.commit_index}.")

        return AppendEntriesResponse(term=self.current_term, success=True, node_id=self.node_id)



    def GetLeader(self, request, context):
        """Handle GetLeader RPC."""
        if self.role == "Leader":
            leader_address = self.node_address
        else:
            leader_address = ""

        return LeaderInfo(leader_address=leader_address)
    
    def GetLastLogIndex(self, request, context):
        """Handle RPC to provide the last log index and term."""
        if len(self.log) == 0:
            return LastLogIndexResponse(last_log_index=-1, last_log_term=0)
        last_index = len(self.log) - 1
        return LastLogIndexResponse(
            last_log_index=last_index,
            last_log_term=self.log[last_index].term
        )

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
