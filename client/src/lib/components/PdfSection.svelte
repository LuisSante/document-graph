<script lang="ts">
    import { onMount } from 'svelte';
    import axios from 'axios';
  
    let message: string = "";
    let loading: boolean = true;
    let error: string | null = null;
  
    onMount(async () => {
      try {
        const response = await axios.get('http://localhost:8300/documents/init');
        message = response.data.message; 
      } catch (err) {
        error = 'Error al conectar con el servidor';
        console.error(err);
      } finally {
        loading = false;
      }
    });
</script>
  
<section>
    {#if loading}
        <p>Loading...</p>
    {:else if error}
        <p class="text-red-500">{error}</p>
    {:else}
        <div class="p-4 border border-gray-300 rounded-lg">
            <h2>Server message:</h2>
            <p>{message}</p>
        </div>
    {/if}
</section>
