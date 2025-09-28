import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, doc, setDoc, updateDoc, onSnapshot, collection, query, where, writeBatch, getDocs } from 'firebase/firestore';

const App = () => {
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const timeSlots = ['9:00 - 10:00', '10:00 - 11:00', '11:00 - 12:00', '12:00 - 1:00', '2:00 - 3:00'];

    const [timetable, setTimetable] = useState([]);
    const [users, setUsers] = useState([]);
    const [stats, setStats] = useState({});
    const [isLoading, setIsLoading] = useState(true);
    const [isAuthReady, setIsAuthReady] = useState(false);
    const [userId, setUserId] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentSlot, setCurrentSlot] = useState(null);
    const [changeReason, setChangeReason] = useState('');
    const [modalMessage, setModalMessage] = useState('');

    const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};
    const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
    const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null;

    useEffect(() => {
        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);
        const db = getFirestore(app);

        const authStateChanged = onAuthStateChanged(auth, async (user) => {
            if (user) {
                setUserId(user.uid);
            } else {
                setUserId(null);
            }
            setIsAuthReady(true);
        });

        // Sign in anonymously if no auth token is present
        if (!initialAuthToken) {
            signInAnonymously(auth).catch((error) => console.error("Anonymous sign-in failed:", error));
        }

        return () => authStateChanged();
    }, []);

    useEffect(() => {
        if (!isAuthReady || !userId) return;

        const db = getFirestore(initializeApp(firebaseConfig));

        // Listener for the latest timetable
        const qTimetable = query(collection(db, `artifacts/${appId}/public/data/timetables`));
        const unsubscribeTimetable = onSnapshot(qTimetable, (snapshot) => {
            const timetables = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
            timetables.sort((a, b) => b.version.seconds - a.version.seconds);
            const latestTimetable = timetables[0];

            if (latestTimetable) {
                const qSlots = collection(db, `artifacts/${appId}/public/data/timetables/${latestTimetable.id}/slots`);
                const unsubscribeSlots = onSnapshot(qSlots, (slotSnapshot) => {
                    const slots = slotSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                    setTimetable(slots);
                    calculateStats(slots);
                    setIsLoading(false);
                }, (error) => console.error("Error fetching slots:", error));
                return () => unsubscribeSlots();
            } else {
                setTimetable([]);
                setStats({});
                setIsLoading(false);
            }
        }, (error) => console.error("Error fetching timetables:", error));

        // Listener for users (for leaderboard)
        const usersRef = collection(db, `artifacts/${appId}/public/data/users`);
        const unsubscribeUsers = onSnapshot(usersRef, (snapshot) => {
            const fetchedUsers = snapshot.docs.map(doc => doc.data()).sort((a, b) => b.approval_points - a.approval_points);
            setUsers(fetchedUsers);
        }, (error) => console.error("Error fetching users:", error));

        // Clean up listeners on component unmount
        return () => {
            unsubscribeTimetable();
            unsubscribeUsers();
        };

    }, [isAuthReady, userId]);

    const calculateStats = (slots) => {
        const total_slots = slots.length;
        const approved_slots = slots.filter(s => s.approval_status === 'approved').length;
        const approval_progress = total_slots > 0 ? Math.round((approved_slots / total_slots) * 100) : 0;
        
        const occupiedRoomSlots = new Set();
        const teacherLoads = defaultdict(0);
        
        slots.forEach(slot => {
            occupiedRoomSlots.add(`${slot.room_id}-${slot.day}-${slot.slot_index}`);
            teacherLoads[slot.teacher_name] += 1;
        });

        const totalRooms = 3; // Simplified, based on initial data
        const totalDays = 5;
        const totalSlotsPerDay = 5;
        const totalPossibleSlots = totalRooms * totalDays * totalSlotsPerDay;
        const utilization = totalPossibleSlots > 0 ? Math.round((occupiedRoomSlots.size / totalPossibleSlots) * 100) : 0;

        let load_status = "Balanced";
        if (Object.keys(teacherLoads).length > 1) {
            const loads = Object.values(teacherLoads);
            if (Math.max(...loads) - Math.min(...loads) > 4) {
                load_status = "Uneven";
            }
        }
        
        setStats({ total_slots, approved_slots, approval_progress, utilization, load_status });
    };

    const openModal = (slot) => {
        setCurrentSlot(slot);
        setChangeReason('');
        setModalMessage('');
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setCurrentSlot(null);
    };

    const handleApprove = async () => {
        if (!currentSlot || !userId) return;
        
        const db = getFirestore(initializeApp(firebaseConfig));
        const batch = writeBatch(db);
        
        const slotRef = doc(db, `artifacts/${appId}/public/data/timetables/${currentSlot.timetable_id}/slots/${currentSlot.id}`);
        batch.update(slotRef, { approval_status: 'approved', approved_by_id: userId });

        const userRef = doc(db, `artifacts/${appId}/public/data/users`, userId);
        const userDoc = await getDocs(userRef);
        
        // This is a simple update. A proper implementation would use transactions
        // to handle concurrent updates to approval_points
        const userPoints = userDoc.exists() ? userDoc.data().approval_points : 0;
        batch.set(userRef, { approval_points: userPoints + 10, username: 'anonymous' }, { merge: true });
        
        await batch.commit();
        setModalMessage(`Approved! You now have ${userPoints + 10} points.`);
        closeModal();
    };

    const handleRequestChange = async () => {
        if (!currentSlot || !userId) return;
        if (!changeReason.trim()) {
            setModalMessage('Please provide a reason for the change request.');
            return;
        }

        const db = getFirestore(initializeApp(firebaseConfig));
        const batch = writeBatch(db);
        
        const slotRef = doc(db, `artifacts/${appId}/public/data/timetables/${currentSlot.timetable_id}/slots/${currentSlot.id}`);
        batch.update(slotRef, { approval_status: 'change_requested', change_reason: changeReason });

        const userRef = doc(db, `artifacts/${appId}/public/data/users`, userId);
        const userDoc = await getDocs(userRef);
        const userPoints = userDoc.exists() ? userDoc.data().approval_points : 0;
        batch.set(userRef, { approval_points: userPoints - 2, username: 'anonymous' }, { merge: true });

        await batch.commit();
        setModalMessage(`Change requested. You now have ${userPoints - 2} points.`);
        closeModal();
    };

    const renderTimetable = () => {
        const slotMap = timetable.reduce((acc, slot) => {
            if (!acc[slot.day]) acc[slot.day] = {};
            acc[slot.day][slot.slot_index] = slot;
            return acc;
        }, {});

        return (
            <div className="timetable-grid">
                <div className="grid-header">Time</div>
                {days.map(day => (
                    <div key={day} className="grid-header">{day}</div>
                ))}
                {timeSlots.map((time, slotIndex) => (
                    <React.Fragment key={time}>
                        <div className="grid-header">{time}</div>
                        {days.map(day => {
                            const slot = slotMap[day]?.[slotIndex];
                            const statusClass = slot ? `slot-${slot.approval_status}` : '';
                            return (
                                <div
                                    key={`${day}-${slotIndex}`}
                                    className={`grid-cell ${statusClass} flex-col cursor-pointer hover:shadow-lg transition-all duration-200`}
                                    onClick={() => slot && openModal(slot)}
                                >
                                    {slot ? (
                                        <>
                                            <div className="font-semibold">{slot.subject_name}</div>
                                            <div className="text-xs text-gray-500">{slot.teacher_name}</div>
                                            <div className="text-xs text-gray-500">{slot.batch_name}</div>
                                        </>
                                    ) : (
                                        <span className="text-sm text-gray-400">Free</span>
                                    )}
                                </div>
                            );
                        })}
                    </React.Fragment>
                ))}
            </div>
        );
    };

    return (
        <div className="p-8 bg-gray-100 min-h-screen">
            <header className="flex justify-between items-center mb-8 pb-4 border-b border-gray-300">
                <h1 className="text-3xl font-bold text-gray-800">ClassChord Dashboard</h1>
                <a href="/" className="text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors">
                    Go to Generator
                </a>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 bg-white rounded-xl shadow-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-2xl font-bold text-gray-800">Timetable Overview</h2>
                        {isLoading && (
                            <svg className="animate-spin h-6 w-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        )}
                    </div>
                    {isAuthReady && userId && <div className="text-xs text-gray-400 mb-4">Current User ID: {userId}</div>}
                    {renderTimetable()}
                </div>

                <div className="md:col-span-1 space-y-6">
                    <div className="bg-white rounded-xl shadow-lg p-6">
                        <h3 className="text-xl font-bold text-gray-800 mb-4">Analytics</h3>
                        <div className="space-y-4 text-sm text-gray-700">
                            <div><span className="font-medium">Total Slots:</span><span className="float-right text-gray-600">{stats.total_slots || 0}</span></div>
                            <div><span className="font-medium">Approved Slots:</span><span className="float-right text-gray-600">{stats.approved_slots || 0}</span></div>
                            <div><span className="font-medium">Approval Progress:</span><span className="float-right text-green-600 font-semibold">{stats.approval_progress || 0}%</span></div>
                            <div><span className="font-medium">Room Utilization:</span><span className="float-right text-blue-600 font-semibold">{stats.utilization || 0}%</span></div>
                            <div><span className="font-medium">Faculty Load:</span><span className="float-right text-gray-600">{stats.load_status || '...'}</span></div>
                        </div>
                    </div>

                    <div className="bg-white rounded-xl shadow-lg p-6">
                        <h3 className="text-xl font-bold text-gray-800 mb-4">User Leaderboard</h3>
                        <ul className="space-y-2">
                            {users.map(user => (
                                <li key={user.username} className="flex justify-between items-center text-gray-700">
                                    <span className="font-medium">{user.username}</span>
                                    <span className="bg-gray-200 text-gray-800 text-xs font-semibold px-2.5 py-0.5 rounded-full">{user.approval_points} points</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </div>

            {isModalOpen && currentSlot && (
                <div className="modal-overlay fixed inset-0 flex items-center justify-center bg-gray-600 bg-opacity-50">
                    <div className="bg-white rounded-lg p-8 max-w-lg w-full shadow-2xl">
                        <h3 className="text-2xl font-bold mb-4 text-gray-800">Slot Details</h3>
                        <div className="text-gray-700 space-y-2">
                            <p><span className="font-semibold">Subject:</span> {currentSlot.subject_name}</p>
                            <p><span className="font-semibold">Teacher:</span> {currentSlot.teacher_name}</p>
                            <p><span className="font-semibold">Batch:</span> {currentSlot.batch_name}</p>
                            <p><span className="font-semibold">Room:</span> {currentSlot.room_id}</p>
                            <p><span className="font-semibold">Time:</span> {currentSlot.day}, Slot {currentSlot.slot_index}</p>
                            <p><span className="font-semibold">Status:</span> {currentSlot.approval_status}</p>
                            {currentSlot.change_reason && <p className="mt-4 text-sm"><span className="font-semibold">Reason:</span> {currentSlot.change_reason}</p>}
                        </div>

                        {currentSlot.approval_status === 'pending' && (
                            <div className="mt-6 flex flex-col space-y-4">
                                <div>
                                    <label htmlFor="changeReason" className="block text-sm font-medium text-gray-700 mb-2">
                                        Reason for change request:
                                    </label>
                                    <textarea
                                        id="changeReason"
                                        className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
                                        rows="2"
                                        value={changeReason}
                                        onChange={(e) => setChangeReason(e.target.value)}
                                    ></textarea>
                                </div>
                                <div className="flex justify-end space-x-4">
                                    <button onClick={closeModal} className="px-6 py-2 border border-gray-300 text-gray-700 rounded-full font-medium transition-colors hover:bg-gray-200">
                                        Cancel
                                    </button>
                                    <button onClick={handleRequestChange} className="px-6 py-2 bg-red-500 text-white rounded-full font-medium transition-colors hover:bg-red-600">
                                        Request Change
                                    </button>
                                    <button onClick={handleApprove} className="px-6 py-2 bg-green-500 text-white rounded-full font-medium transition-colors hover:bg-green-600">
                                        Approve
                                    </button>
                                </div>
                            </div>
                        )}
                        {currentSlot.approval_status !== 'pending' && (
                            <div className="mt-6 flex justify-end">
                                <button onClick={closeModal} className="px-6 py-2 border border-gray-300 text-gray-700 rounded-full font-medium transition-colors hover:bg-gray-200">
                                    Close
                                </button>
                            </div>
                        )}

                        {modalMessage && (
                            <div className="mt-4 p-3 text-center text-sm font-medium text-white bg-blue-500 rounded-lg">
                                {modalMessage}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default App;
