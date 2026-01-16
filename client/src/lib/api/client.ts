import axios from 'axios';
import { PUBLIC_DEV_LOCAL } from '$env/static/public';

export const api = axios.create({
	baseURL: PUBLIC_DEV_LOCAL, 
	withCredentials: false
});
