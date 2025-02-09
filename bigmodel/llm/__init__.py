# 确保所有模型提供者被导入，用于自动注册，虽然没有用到，但是不能删除，删除了的话，就不会触发register的注解了
from . import providers 