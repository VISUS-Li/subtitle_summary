# 确保所有工作流模块被导入，用于自动注册，虽然没有用到，但是不能删除，删除了的话，就不会触发register的注解了
from . import subtitle
from . import qa


# 可以在这里添加其他工作流模块的导入 