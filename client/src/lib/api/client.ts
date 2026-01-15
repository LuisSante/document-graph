import axios from 'axios';

export const api = axios.create({
	baseURL: 'http://localhost:8300/api', 
	withCredentials: false
});
