<script setup lang="ts">
// 预留实现
</script>

<template>
  <div class="history-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>历史记录</span>
        </div>
      </template>
      
      <el-empty description="功能开发中..." />
    </el-card>
  </div>
</template>

<style scoped>
.history-container {
  min-height: calc(100vh - 100px);
}

.card-header {
  font-weight: bold;
}
</style> 